from datetime import datetime

import re

from Rambler import component, option, outlet, nil, field


#index = copmonent.entity.index
#field = component.entity.field

# TODO: Review the message code and handle_response methods to ensure that we're doing the right thing.  
class Session(component('Entity')):
  id                      = field(str)
  key_vals                = field(dict, default=dict)

  #TDOO: entity.time_stamps() should do the equivalent of the following
  created_at              = field(datetime)
  
  def value_for_undefined_key(self, key):
    try:
      return self.key_vals[key]
    except KeyError:
      raise AttributeError
      
  def set_value_for_undefined_key(self, value, key):
    self.key_vals[key] = value
    
  def get(self, *args, **kw):
    return self.key_vals.get(*args, **kw)
  
  def clear(self):
    # Clear all session values
    self.key_vals.clear()
