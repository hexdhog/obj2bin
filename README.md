# obj2bin

A simple object serialization library. Define the packet structure and let obj2bin deal with the serialization.

```python
import binascii

from obj2bin import Const, Field, packet, encode, decode, utf8tobytes, utf8frombytes, utf8size

@packet(
  packet_id=Const(1, "B"),
  user_id=Field(">H"),
  name_size=Field("B", meta=True),
  name=Field("<{name_size}s", enc=utf8tobytes, dec=utf8frombytes)
)
class User:
  user_id: int
  name: str
  @property
  def name_size(self) -> int: return utf8size(self.name)

user = User(13, "John")
print(user)
buff, size = encode(user)
print(binascii.hexlify(buff).decode("utf-8"), size)
print(*decode(User, buff))

# output:
#   User(user_id=13, name='John')
#   01000d044a6f686e 8
#   User(user_id=13, name='John') 8
```

> **_Note:_**  Refer to [example.py](example.py) for a more complete demonstration.

Python's [struct module](https://docs.python.org/3/library/struct.html) is used to serialize data to bytes. How each object attribute is serialized is determined by the `fmt` parameter which expects a [struct format string](https://docs.python.org/3/library/struct.html#struct-format-strings).

The order the packet fields will be encoded is determined by the order of the keyword arguments passed to the `@packet()` decorator. Because of this, dictionary insertion order must be maintained and, therefore, **obj2bin requires [Python >= 3.7](https://stackoverflow.com/questions/39980323/are-dictionaries-ordered-in-python-3-6#answer-39980744)**. This requirement is planned to be removed in the future.

## Packet field types

#### Field

A packet field with a dynamic value. The value to be serialized is taken from the object's attribute whose name matches the keyword entry name.

#### Const

A packet field with a constant value. If, when being decoded, the value does not match the one specified in Const an exception will be raised. Useful for defining attributes which identify a packet (e.g. packet type identifier or version).

#### Child

A packet field which serializes another packet object. Multiple packet object can be specified for the same field.
