''' Tests whether all the visa drivers included in lightlab are properly
coded. All tests should be safe to run locally.'''

import pytest
from mock import patch
from lightlab.equipment.lab_instruments import visa_drivers
import inspect

classes = []
for name, obj in inspect.getmembers(visa_drivers):
    if inspect.isclass(obj):
        classes.append(obj)


class OpenError(RuntimeError):
    pass


@pytest.mark.parametrize("instrum", classes)
def test_instantinstrum(instrum):
    ''' Instatiates instruments and asserts that .open should not be called
    '''
    def open_error(self):
        raise OpenError("self.open() function being called upon initialization.")
    with patch.object(instrum, 'open', open_error):
        instrum()