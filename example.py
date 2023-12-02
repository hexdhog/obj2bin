#!/usr/bin/env python3
# mypy: ignore-errors
from __future__ import annotations

import time
import binascii

from pypacket import (
  Const,
  Field,
  Child,
  packet,
  calcsize,
  utf8size,
  utf8tobytes,
  utf8frombytes,
  encode,
  decode
)

# the packet decorator is used to specify the structure of the packet, indicating how each field must be serialized
@packet(
  # each object attribute to include in the serialization is specified with its name as the parameter name and a Field object as its value
  # the first argument to Field is the format string (from python's struct module) to be used to encode/decode the attribute
  # the enc and dec arguments allow to specify a function which will be called before/after the attribute is encoded/decoded
  #   NOTE:
  #     the order of the parameters will determine the order they are serialized
  #     the return type of the enc function must match the type specified in the format string
  #     the return type of the dec function must match the class' attribute type
  x=Field("<H", enc=lambda x: int(x * 100), dec=lambda x: float(x / 100)), # unsigned short little-endian
  y=Field("@H", enc=lambda x: int(x * 100), dec=lambda x: float(x / 100)), # unsigned short with native order
)
# a class is defined with the same parameters passed to the packet decorator as class attributes
class Point:
  x: float
  y: float

# the packet decorator will return the processed class as a dataclass, therefore, an object can be created as follows
p = Point(420.69, 13.37)
print(p) # Point(x=420.69, y=13.37)
# to encode the object the encode() function is used
# a bytearray buffer and offset can be passed through the buffer and offset parameters (in case you need to encode different object to the same buffer)
buff, size = encode(p) # buff: bytearray buffer with encoded object, s: encoded object size
print(binascii.hexlify(buff).decode("utf-8"), size) # 55a43905 4
# to decode the object the decode() function is used with the expected type to decode as the first parameter and the data buffer to decode from as the second
print(*decode(Point, buff), end="\n\n") # Point(x=420.69, y=13.37) 4

# packets can also have variable-sized fields (e.g. strings)
# two different fields are used to specify a variable-sized field, the first indicating the second's size
@packet(
  age=Field("B"),
  height=Field("f"),
  weight=Field("f"),
  # meta=True indicates that this is a metadata field (its value depends on another field)
  name_size=Field("B", meta=True),
  # the name of the field indicating the name size is specified between curly braces in the format string
  name=Field("{name_size}s", enc=utf8tobytes, dec=utf8frombytes)
)
class Person:
  age: int
  height: float
  weight: float
  name: str
  # a property is defined to indicate the current size of the field
  @property
  def name_size(self) -> int: return utf8size(self.name)

p = Person(22, 180.0, 66.75, "Fogell McLovin")
print(p) # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin')
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size) # 1600003443008085420e466f67656c6c204d634c6f76696e 24
print(*decode(Person, buff), end="\n\n") # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin') 24

# it is very common to have some packet fields as control fields (e.g. packet header to identify the packet type and/or packet version), this can be done with the Const class
# a Const has the same parameters as Field except for the first one, which indicates its value
# when decoding a Const, if the decoded value does not match the expected value an error will be raised
@packet(
  _id=Const(0x45, "B"), # packet id (identifies the packet type with a unique value)
  _version=Const(0x01, "B"), # packet version (indicates the packet type version)
  unixtime=Field("L")
)
class Time:
  unixtime: int

t = Time(int(time.time()))
print(t) # Time(unixtime=1697915180)
buff, size = encode(t)
print(binascii.hexlify(buff).decode("utf-8"), size) # 45016534212c 6
print(*decode(Time, buff), end="\n\n") # Time(unixtime=1697915180) 6

# the size of bytes of an object can be calculated using the calcsize() function
print(p, calcsize(p)) # Person(age=22, height=180.0, weight=66.75, name='Fogell McLovin') 24
print(t, calcsize(t), end="\n\n") # Time(unixtime=1697964674) 6

# a packet can also have other packet objects as childs, this can be done with the Child class
@packet(
  _id=Const(0xff, "B"),
  # specify the expected object types as positional arguments to Child
  # the count parameter specifies the amount of packet child objects
  # if count=1 then the attribute is treated like an object, instead of a list (note the type annotations on the class' attributes)
  person=Child(Person, count=1),
  register_timestamp=Child(Time, count=1),
  # Child can also a dynamic size/count
  # this can be achieved by creating a separate Field with meta=True and indicating its name in the size/count parameter of Child
  friends_size=Field("H", meta=True),
  friends=Child(Person, size="friends_size"), # size indicates the number of bytes of the whole field (see friends_size property)
  enemies_count=Field("H", meta=True),
  enemies=Child(Person, count="enemies_count") # count indicates the number of objects in the field (see enemies_count property)
)
class Player:
  person: Person
  register_timestamp: Time
  friends: list[Person]
  enemies: list[Person]
  # property indicating the number of bytes in the friends attribute
  @property
  def friends_size(self) -> int: return sum(calcsize(x) for x in self.friends)
  # property indicating the amount of object in the enemies attribute
  @property
  def enemies_count(self) -> int: return len(self.enemies)

p = Player(
  Person(21, 173.0, 59.75, "Jim"),
  Time(int(time.time())),
  [Person(20, 180.0, 65.25, "Michael"), Person(25, 190.75, 80.0, "Pam"), Person(26, 187.0, 89.0, "Darryl")],
  [Person(20, 200.0, 88.0, "Dwight"), Person(19, 188.0, 78.0, "Mose")]
)
print(p)
# Player(
#   person=Person(age=21, height=173.0, weight=59.75, name='Jim'),
#   register_timestamp=Time(unixtime=1697964823),
#   friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')],
#   enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')])
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size)
# ff15432d0000426f0000034a696d45016534e317002e144334000042828000074d69636861656c19433ec00042a000000350616d1a433b000042b200000644617272796c0002144348000042b000000644776967687413433c0000429c0000044d6f7365 100
print(*decode(Player, buff), end="\n\n")
# Player(
#   person=Person(age=21, height=173.0, weight=59.75, name='Jim'),
#   register_timestamp=Time(unixtime=1697964823),
#   friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')],
#   enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]) 100

# if a Child does not have a size or count it will be encoded/decoded until the end of the object list/byte stream
@packet(points=Child(Point))
class PointList:
  points: list[Point]

p = PointList([Point(10.25, 125.0)] * 5)
print(p) # PointList(points=[Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0)])
buff, size = encode(p)
print(binascii.hexlify(buff).decode("utf-8"), size) # 0104d4300104d4300104d4300104d4300104d430 20
print(*decode(PointList, buff), end="\n\n") # PointList(points=[Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0), Point(x=10.25, y=125.0)]) 20

# a Child can also have arbitrarily many packet subtypes with any order (only if each packet subtype has some Const identifying it)
@packet(objects=Child(Time, Player))
class Dummy:
  objects: list[Time | Player]

d = Dummy([
    Time(int(time.time())),
    Player(
      Person(21, 173.0, 59.75, "Jim"),
      Time(int(time.time())),
      [Person(20, 180.0, 65.25, "Michael"), Person(25, 190.75, 80.0, "Pam"), Person(26, 187.0, 89.0, "Darryl")],
      [Person(20, 200.0, 88.0, "Dwight"), Person(19, 188.0, 78.0, "Mose")]
    ),
    Time(int(time.time()))
  ]
)
print(d)
# Dummy(objects=[
#   Time(unixtime=1697966449),
#   Player(person=Person(age=21, height=173.0, weight=59.75, name='Jim'), register_timestamp=Time(unixtime=1697966449), friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')], enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]),
#   Time(unixtime=1697966449)])
buff, size = encode(d)
print(binascii.hexlify(buff).decode("utf-8"), size)
# 45016534e971ff15432d0000426f0000034a696d45016534e971002e144334000042828000074d69636861656c19433ec00042a000000350616d1a433b000042b200000644617272796c0002144348000042b000000644776967687413433c0000429c0000044d6f736545016534e971 112
print(*decode(Dummy, buff), end="\n\n")
# Dummy(objects=[
#   Time(unixtime=1697966449),
#   Player(person=Person(age=21, height=173.0, weight=59.75, name='Jim'), register_timestamp=Time(unixtime=1697966449), friends=[Person(age=20, height=180.0, weight=65.25, name='Michael'), Person(age=25, height=190.75, weight=80.0, name='Pam'), Person(age=26, height=187.0, weight=89.0, name='Darryl')], enemies=[Person(age=20, height=200.0, weight=88.0, name='Dwight'), Person(age=19, height=188.0, weight=78.0, name='Mose')]),
#   Time(unixtime=1697966449)]) 112

# a Field can also encode/decode an arbitrary amount of values delimited by a stop value
# for example, let's define an object with a Field which stores an array of 8 bit integers using the value 255 (0xff) as the delimiter
# so, when the Field is encoded, the stop value will be appended to the end of the Field's buffer
# likewise, when the Field is decoded, all values in the data buffer will be decoded until the stop value is found
@packet(
  value=Field(
    "B", # encode each element of the value list as byte
    stop=0xff # use 255 as the stop value
  )
)
class Int8Array:
  value: list[int]

d = Int8Array([1, 2, 3, 4, 5, 6, 7, 8, 9])
print(d)
# Int8Array(value=[1, 2, 3, 4, 5, 6, 7, 8, 9])
buff, size = encode(d)
print(binascii.hexlify(buff).decode("utf-8"), size)
# 010203040506070809ff 10
print(*decode(Int8Array, buff), end="\n\n")
# Int8Array(value=[1, 2, 3, 4, 5, 6, 7, 8, 9]) 10

# the following example implements a null terminated string object
# the functions below are used, alongside utf8tobytes and utf8frombytes, to encode and decode the null terminated string
# it is important to note that the encode function/s will be called twice, once with the Field's attribute's value as argument and an other time with the stop value as argument
# whereas the decode function/s will be called for each element in the Field's buffer until the stop value is found
def bytestoint8(val: bytes) -> list[int]: return [x if isinstance(x, int) else int.from_bytes(x) for x in val]
def int8tobytes(val: int) -> bytes: return val.to_bytes(1)

@packet(
  value=Field(
    "B", # encode each string character as a byte
    stop="\x00", # use a null byte as the stop value (must be a string as it will be processed by the encode/decode functions)
    enc=(utf8tobytes, bytestoint8), # first convert the utf-8 string to bytes, then convert each byte to an int8
    dec=(int8tobytes, utf8frombytes) # first convert the int8 to bytes, then convert the byte to a utf-8 string
  )
)
class String:
  value: str

  # the constructor allows the string value to be passed as a string or as a list of characters
  # because when the object is decoded the string will be split into an array of characters
  def __init__(self, value: str | list[str]):
    if isinstance(value, list): value = "".join(value)
    self.value = value

s = String("this is a null terminated string object")
print(s)
# String(value='this is a null terminated string object')
buff, size = encode(s)
print(binascii.hexlify(buff).decode("utf-8"), size)
# 746869732069732061206e756c6c207465726d696e6174656420737472696e67206f626a65637400 40
print(*decode(String, buff), end="\n\n")
# String(value='this is a null terminated string object') 40
