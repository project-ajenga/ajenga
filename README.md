# Ajenga
[![License](https://img.shields.io/github/license/project-ajenga/ajenga.svg)](LICENSE)


## Installation

```bash
pip install git+https://github.com/project-ajenga/Core.git
pip install git+https://github.com/project-ajenga/Router.git
pip install git+https://github.com/project-ajenga/Protocol.git
```

## Usage

Create a config.py script
```python
from ajenga.default_config import *

# Your customized config
```

Create a run.py script, assuming using onebot
```python
import asyncio
import ajenga
import config

ajenga.init_config(config)

import ajenga.plugin
from ajenga.protocol.cqhttp import CQProtocol

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(CQProtocol().run_task(host='127.0.0.1', port=8080))
    # loop.create_task(ajenga.plugin.load_plugin(module_path='plugins.plugin_manager'))
    loop.run_forever()

```

Then write and add your plugins.

