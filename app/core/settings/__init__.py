from decouple import config

is_running_in_prod = config('PROD_ENVIROMENT', cast=bool, default=False)
if is_running_in_prod:
    from .prod import *
else:
    from .dev import *