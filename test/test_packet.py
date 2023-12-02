#!/usr/bin/env python3
# mypy: disable-error-code=call-arg
from __future__ import annotations

import unittest

from pypacket import Const, Field, Child, packet, calcsize, encode, decode, utf8size, utf8tobytes, utf8frombytes

@packet(_id=Const(0, "B"), value=Field("i"))
class DummyInt:
  value: int

@packet(_id=Const(1, "B"), value=Field("f"))
class DummyFloat:
  value: int

@packet(_id=Const(2, "B"), size=Field("H", meta=True), value=Field("{size}s"))
class DummyString:
  value: str
  @property
  def size(self) -> int: return utf8size(self.value)

@packet(
  const_be=Const(0x1337, ">H"),
  const_le=Const(0x1337, "<H"),
  field_be=Field(">H"),
  field_le=Field("<H")
)
class DummyByteOrder:
  field_be: int
  field_le: int

@packet(childs=Child(DummyInt, DummyFloat, DummyByteOrder))
class DummyChild:
  childs: list

@packet(
  childs_int=Child(DummyInt, DummyFloat, DummyByteOrder, count=3),
  size_str=Field("B", meta=True),
  childs_str=Child(DummyInt, DummyFloat, DummyByteOrder, count="size_str")
)
class DummyChildCount:
  childs_int: list
  childs_str: list
  @property
  def size_str(self) -> int: return len(self.childs_str)

@packet(
  childs_int=Child(DummyInt, size=calcsize(DummyInt(0)) * 2, count=2),
  size_str=Field("B", meta=True),
  childs_str=Child(DummyInt, DummyFloat, DummyByteOrder, size="size_str")
)
class DummyChildSize:
  childs_int: list
  childs_str: list
  @property
  def size_str(self) -> int: return len(self.childs_str)

def _strtotuple(x: str) -> tuple[int, ...]: return tuple(int(x[i:i+2]) for i in range(0, len(x), 2))
def _tupletostr(x: tuple) -> str: return "".join(f"{n:02d}" for n in x)

@packet(
  const=Const(
    "0102030405060708",
    "8B",
    enc=_strtotuple,
    dec=_tupletostr
  ),
  field=Field(
    "16s",
    enc=(_tupletostr, utf8tobytes),
    dec=(utf8frombytes, _strtotuple)
  )
)
class DummyEncDec:
  field: tuple[int, ...]

@packet(value=Field("B", meta=True))
class DummyFieldMeta:
  value: int = 0

class TestPacket(unittest.TestCase):
  # def test_dummy_count_size(self) -> None:
  #   # TODO: rethink test
  #   # child count
  #   self.assertRaises(AssertionError, lambda: encode(DummyChildCount([DummyInt(0), DummyFloat(0.0)], [])))
  #   self.assertRaises(AssertionError, lambda: encode(DummyChildCount([DummyInt(0), DummyFloat(0.0), DummyByteOrder(0, 0), DummyInt(0)], [])))
  #   dummy = DummyChildCount([DummyInt(0), DummyFloat(0.0), DummyByteOrder(0, 0)], [])
  #   buff = bytearray(encode(dummy)[0])
  #   buff.append(5)
  #   obj, _ = decode(DummyChildCount, buff)
  #   assert obj == dummy
  #
  #   # child size
  #   # dummy = DummyChildSize([], [])

  def test_calcsize(self) -> None:
    assert calcsize(DummyInt(0)) == 5
    assert calcsize(DummyFloat(0.0)) == 5
    assert calcsize(DummyByteOrder(0, 0)) == 8
    assert calcsize(DummyChild([DummyInt(0), DummyFloat(0.0), DummyByteOrder(0, 0)])) == 18

  def test_buffer_and_offset(self) -> None:
    dummy = DummyByteOrder(0, 0)
    buff, size = encode(dummy)
    assert len(buff) == size, "buffer size does not match returned size"
    buffer = bytearray(size * 2)
    buff, size = encode(dummy, buffer)
    buffer[0:size] = buff
    buff, size = encode(dummy, buffer, size)
    buffer[size:size+size] = buff
    d1, size = decode(DummyByteOrder, buffer)
    d2, size = decode(DummyByteOrder, buffer, size)
    assert d1 == d2 == dummy

  def test_order(self) -> None:
    buff, _ = encode(DummyByteOrder(0x1337, 0x1337))
    assert buff[0] == 0x13 and buff[1] == 0x37, "incorrect Const big-endian order"
    assert buff[2] == 0x37 and buff[3] == 0x13, "incorrect Const little-endian order"
    assert buff[4] == 0x13 and buff[5] == 0x37, "incorrect Field big order"
    assert buff[6] == 0x37 and buff[7] == 0x13, "incorrect Field little-endian order"
    for name, val in vars(decode(DummyByteOrder, buff)[0]).items(): assert val == 0x1337, f"incorrect decoded value for Field \"{name}\""

  def test_enc_dec(self) -> None:
    dummy = DummyEncDec((8, 7, 6, 5, 4, 3, 2, 1))
    buff, _ = encode(dummy)
    obj, _ = decode(DummyEncDec, buff)
    assert obj == dummy

  def test_field_meta(self) -> None:
    dummy = DummyFieldMeta()
    dummy.value = 1
    buff, _ = encode(dummy)
    obj, _ = decode(DummyFieldMeta, buff)
    assert dummy.value == 1 and obj.value == 0

if __name__ == "__main__":
  unittest.main()
