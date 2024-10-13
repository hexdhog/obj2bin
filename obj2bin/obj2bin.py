from __future__ import annotations

from functools import reduce
from contextlib import suppress
from dataclasses import dataclass
from platform import python_version_tuple
from typing import TypeVar, Callable, Iterable, Any
from struct import pack_into, unpack_from, calcsize as calcsize_fmt

# TODO: add stop option to Child?

# python >= 3.7 needed for ordered dictionaries
assert tuple(map(int, python_version_tuple()))[0:2] >= (3, 7), "unsupported python version (>=3.7)"

_T = TypeVar("_T")
_STOP = "stop"
_PATTRS = "_pattrs"

def utf8size(s: str) -> int: return len(s)
def utf8tobytes(s: str) -> bytes: return bytes(s, "utf-8")
def utf8frombytes(b: bytes) -> str: return b.decode("utf-8")
def vargs(fn: Callable[..., Any]) -> Callable[..., Any]: return lambda x: fn(*x)
def totuple(val: object) -> list | tuple: return tuple(val) if hasattr(val, "__iter__") else (val,)
def expifsingle(val: list | tuple | object) -> list | tuple | object: return val[0] if isinstance(val, (tuple, list)) and len(val) == 1 else val
def fnwalk(fn: Callable[..., Any] | Iterable[Callable[..., Any]] | None, *args: tuple) -> object | None:
  return reduce(lambda v, f: f(expifsingle(v)) if callable(f) else v, [args, *fn] if isinstance(fn, (tuple, list)) else [args, fn])

class PackAttribute:
  def __init__(self, enc: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None, dec: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None): self.enc, self.dec = enc, dec
  def process(self, fn: Callable[..., Any] | Iterable[Callable[..., Any]] | None, val: object) -> object:
    if not isinstance(val, (tuple, list)): val = [val]
    return expifsingle(fnwalk(fn, *val))
  def encode(self, val: object) -> object: return self.process(self.enc, val)
  def decode(self, val: object) -> object: return self.process(self.dec, val)

class Field(PackAttribute):
  def __init__(self, fmt: str, stop: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None,
               enc: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None, dec: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None, meta: bool = False):
    self.fmt, self.stop, self.enc, self.dec, self.meta = fmt, stop, enc, dec, meta

class Const(PackAttribute):
  def __init__(self, value: object, fmt: str, enc: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None, dec: Callable[..., Any] | Iterable[Callable[..., Any]] | None = None):
    self.value, self.fmt, self.enc, self.dec = value, fmt, enc, dec

class Child:
  def __init__(self, *childs: type, size: int | str = 0, count: int | str = 0): self.childs, self.size, self.count = childs, size, count
  def attrs(self, name: str, vals: dict, obj: object | None = None) -> tuple[list, int, int]:
    size = self.size if isinstance(self.size, int) else 0
    if isinstance(self.size, str): size = vals[self.size]
    count = self.count if isinstance(self.count, int) else 0
    if isinstance(self.count, str): count = vals[self.count]
    childs = getattr(obj, name) if obj is not None else []
    if not isinstance(childs, (tuple, list)): childs = [childs]
    return childs, size, count

def pack(**attrs: Const | Field | Child) -> Callable[[type], type]: return lambda x: setattr(x, _PATTRS, attrs) or dataclass(x) # type: ignore[func-returns-value]
def calcsize(obj: object) -> int:
  # dictionary holding the processed values passed as a variadic argument to format Fields' format string (in case some Field uses another's value as format string)
  vals: dict[str, Any] = {}
  size = 0
  for name, attr in getattr(obj, _PATTRS).items():
    if isinstance(attr, Child):
      size += sum(calcsize(val) for val in attr.attrs(name, vals, obj)[0])
    else:
      vals[name] = attr.encode(attr.value if isinstance(attr, Const) else getattr(obj, name))
      mult = 1 if getattr(attr, _STOP, None) is None else len(totuple(vals[name])) + 1
      size += calcsize_fmt(attr.fmt.format(**vals)) * mult
  return size

def encode(obj: object, buffer: bytearray | None = None, offset: int = 0) -> tuple[bytes, int]:
  vals: dict[str, Any] = {}
  bsize = calcsize(obj)
  if not isinstance(buffer, (bytearray, bytes)): buffer = bytearray(bsize)
  assert offset + bsize <= len(buffer), f"buffer size too small ({len(buffer)}/{offset + bsize})"
  for name, attr in getattr(obj, _PATTRS).items():
    if isinstance(attr, Child):
      childs, size, count, cstart = *attr.attrs(name, vals, obj), offset
      assert len(childs) == count or count <= 0, f"invalid child count {len(childs)} != {count}"
      for val in childs:
        b, s = encode(val)
        buffer[offset:offset+s], offset = b, offset + s
      assert offset - cstart == size or size <= 0, f"invalid child size {offset - cstart} != {size}"
    else:
      val, fmt = attr.encode(attr.value if isinstance(attr, Const) else getattr(obj, name)), attr.fmt.format(**vals)
      vals[name], size, stop = val, calcsize_fmt(fmt), getattr(attr, _STOP, None)
      if stop is None:
        if not isinstance(val, (list, tuple)): val = (val,) # not calling totuple as val might be an iterable object other that list or tuple (e.g. str)
        pack_into(fmt, buffer, offset, *val)
        offset += size
      else:
        for v in [*totuple(val), attr.encode(stop)]:
          pack_into(fmt, buffer, offset, v)
          offset += size
  return bytes(buffer), bsize

def decode(ptype: _T, buffer: bytes | bytearray, offset: int = 0) -> tuple[_T, int]: # noqa: C901
  vals: dict[str, Any] = {}
  start = offset
  assert isinstance(ptype, type), f"\"{type(ptype).__name__}\" is not a type"
  for name, attr in getattr(ptype, _PATTRS).items():
    if isinstance(attr, Child):
      vals[name], size, count, bsize = *attr.attrs(name, vals), 0
      while bsize < size or size <= 0 and (offset < len(buffer) and count <= 0 or offset < len(buffer) and len(vals[name]) < count):
        for subtype in attr.childs:
          if len(vals[name]) >= count > 0: break
          with suppress(Exception):
            obj, s = decode(subtype, buffer, offset)
            bsize, offset = bsize + s, offset + s
            vals[name].append(obj)
            break
      assert len(vals[name]) == count or count <= 0, f"invalid child count {len(vals[name])} != {count}"
      if len(vals[name]) == 1: vals[name] = vals[name][0]
    else:
      fmt, stop = attr.fmt.format(**vals), getattr(attr, _STOP, None)
      if stop is None:
        vals[name], offset = attr.decode(unpack_from(fmt, buffer, offset)), offset + calcsize_fmt(fmt)
      else:
        vals[name] = []
        while True:
          v, offset = attr.decode(unpack_from(fmt, buffer, offset)), offset + calcsize_fmt(fmt)
          if v == stop: break
          vals[name].append(v)
      assert (isinstance(attr, Const) and attr.value == vals[name]) or not isinstance(attr, Const), f"unexpected value found for {ptype.__name__}.{name}: {vals[name]} (expected: {attr.value})"
  for name, attr in getattr(ptype, _PATTRS).items():
    if isinstance(attr, Field) and attr.meta or isinstance(attr, Const): vals.pop(name)
  return ptype(**vals), offset - start
