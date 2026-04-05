import typing
import pydantic.v1.fields
orig_set_default = pydantic.v1.fields.ModelField._set_default_and_type

def _new_set_default(self):
    try:
        orig_set_default(self)
    except pydantic.v1.errors.ConfigError:
        self.type_ = typing.Any
        self.required = False

pydantic.v1.fields.ModelField._set_default_and_type = _new_set_default

import crawler_v2
import asyncio

if __name__ == '__main__':
    asyncio.run(crawler_v2.main())
