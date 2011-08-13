from __future__ import with_statement
import MySQLdb
import inspect

from Rambler import component, outlet, option

try:
  import json
except ImportError:
  import simplejson as json


class MySQLOperation(component('Operation')):
  
  log = outlet('LogService')
    
  db_conf = option('mysql','conf')
  
  connections = {}
  last_operation = None
  block = None
  
  @classmethod
  def connection_for(cls, model):
    conn = cls.connections.get(model)
    if conn is None:
      conn = cls.connections[model] = MySQLdb.connect(**cls.db_conf['default'])
    return conn
  
  @classmethod
  def execute(cls, model, statement, *args):
    """Returns an operation that will executes the give statement."""
    op = cls()
    op.statement = statement
    op.connection = cls.connection_for(model)
    op.vals = args
    if cls.last_operation:
      op.add_dependency(cls.last_operation)
    cls.last_operation = op
    
    return op
    
  @classmethod
  def create(cls, obj):
    """Generates an insert statement and returns a MySQLOperation. """
    
    operation = cls()
    obj.encode_with(operation)       
    operation.connection = cls.connection_for(obj.__class__)
    operation.statement = 'INSERT INTO %s (%s) VALUES (%s)' % (
         cls.tablename_for(obj),
         ','.join(operation.keys),
         ','.join(operation.formats)
         )
         
    if cls.last_operation:
      operation.add_dependency(cls.last_operation)
    cls.last_operation = operation
    
    return operation
    
  @classmethod
  def find(cls, model, retrieval, order=None, limit=None, conditions=None, **kw):
    """
    Arguments:
    
    retrieval: either an column id, a list of column ids, the string 'first' or the string 'all'
    order: Optional list of column names to sort on
    
    """
    conditions = conditions or kw
    operation = cls()
    operation.connection = cls.connection_for(model)
    operation.retrieval = retrieval
    operation.model = model
    
    stmt = ['SELECT * FROM %ss' % model.__name__.lower()]
    if conditions:
      stmt.append('WHERE')
      where_clause = []
      if isinstance(conditions, dict):
        for field, value in conditions.items():
          encode_method_name = 'encode_%s_for' % type(value).__name__
          encode_method = getattr(operation, encode_method_name, operation.encode_object_for)
          encode_method(value, field)
          where_clause.append('%s = %s' % (operation.keys[-1], operation.formats[-1]))
        stmt.append(' AND '.join(where_clause))
      else:
        stmt.append(conditions)
      
      
    if order:
      stmt.append('ORDER BY %s' % ','.join(order))
    
    if retrieval == 'first':
      stmt.append('LIMIT 1')
    elif limit is not None:
      stmt.append('LIMIT %d' % limit)

    operation.statement = ' '.join(stmt)
        
    if cls.last_operation:
      operation.add_dependency(cls.last_operation)
    cls.last_operation = operation
    
    return operation
  #
  @classmethod
  def update(cls, obj):
    """Generates an insert statement and returns a MySQLOperation. """
    operation = cls()
    obj.encode_with(operation)
    operation.connection = cls.connection_for(obj.__class__)
    stmt = ['UPDATE %ss SET' %   obj.__class__.__name__.lower()]

    # this optimization is equiv to
    # for field_name, format in operation.keys, operation.formats:
    #   set_stmts.append('%s = %s' % field_name, format)
    # 
    # stmt.append(','.join(set_stmts))
    stmt.append(','.join(map(lambda x,y: '%s = %s' % (x,y), operation.keys, operation.formats)))
    
    # todo: use the right encode_XX_for method base on id's type
    operation.encode_str_for(obj.id, 'id')
    stmt.append('WHERE id = %s' % operation.formats[-1] )
                                  
    operation.statement = ' '.join(stmt)
  
    if cls.last_operation:
      operation.add_dependency(cls.last_operation)
    cls.last_operation = operation

    return operation
    
  @classmethod
  def maximum(cls, model, column_name, conditions={}):
    where_clause = []
    if conditions:
      where_clause.append("WHERE")
      for key, val in conditions.items():
        where_clause.append("%s = %s" % (key,val))
    where_clause = " ".join(where_clause)
    
    table_name = cls.tablename_for(model)
    
    stmt = "SELECT %s FROM %s %s ORDER BY %s DESC LIMIT 1" % (
      column_name,
      table_name,
      where_clause,
      column_name
    )
    op = cls.execute(model, stmt)
    
    def retmax(r):
      return r[0][0]
    op.block = retmax
    return op
     
     
  @classmethod
  def tablename_for(cls, obj):
    if inspect.isclass(obj):
      name = obj.__name__.lower()
    else:
      name = obj.__class__.__name__.lower()

    if name.endswith('s'):
      name += 'es'
    else:
      name += 's'
    return name
    
  def __init__(self):
    super(MySQLOperation, self).__init__()
    
    self.model     = None
    self.keys      = []
    self.vals      = []
    
    self.formats   = []
    self.statement = None
    self.retrieval = None
    self._result   = None
    
    
  def decode_int_for(self, key):
    return self.vals[self._description[key]]
    
  def decode_float_for(self, key):
    return self.vals[self._description[key]]
    
  def decode_str_for(self, key):
    return self.vals[self._description[key]]
  
  def decode_datetime_for(self, key):
    return self.vals[self._description[key]]
    
  def decode_bool_for(self, key):
    return self.vals[self._description[key]]
    
  def decode_object_for(self, key):
    return json.loads(self.vals[self._description[key]])
    
  def encode_int_for(self, i, key):
    self.keys.append(key)
    self.vals.append(i)
    self.formats.append('%s')
    
  def encode_str_for(self, string, key):
    self.keys.append(key)
    self.vals.append(string)
    self.formats.append('%s')
    
  def encode_bool_for(self, bool, key):
    self.keys.append(key)
    self.vals.append(bool)
    self.formats.append('%s')
    
    
  def encode_datetime_for(self, datetime, key):
    self.keys.append(key)
    self.vals.append(datetime)
    self.formats.append('%s')
        
  def encode_object_for(self, object, key):
    '''Encodes the ojbect as a JSON string'''
    self.keys.append(key)
    self.vals.append(json.dumps(object))
    self.formats.append('%s')
    
  def main(self):
    attempt = 2
    try:
      while attempt:
        try:
          self.log.debug(self.statement, *self.vals)
          cursor = self.connection.cursor()
          cursor.execute(self.statement, self.vals)
          if self.is_cancelled:
            return
          
          if cursor.description:
            # map dbapi description attribute to {field_name: index}
            self._description = dict([(des[0], index) for index, des in  enumerate(cursor.description)])
          self._result = cursor.fetchall()
      
          if self.is_cancelled:
            return
      
          cursor.close()
          self.connection.commit()
          break
        except MySQLdb.OperationalError,e:
          # Operational errors are no-program related errors so retry the statement
          self.forget_connection()
          self.log.exception('mysql operational error retrying')
          attempt -= 1
    except Exception, e:
      # Return all other exceptions
      self.forget_connection()
      self.log.exception('running %s %s', self.statement, self.vals)
      self._result = e

  def forget_connection(self):
      
    for key, conn in self.connections.items():
      if conn == self.connection:
        self.log.warn('Forgetting connection')
        del self.connections[key]
        break
        
    try:
      self.connection.close()
    except:
      pass

      
  @property
  def result(self):
    if isinstance(self._result, Exception):
      raise self._result
    else:
      if self.block:
        return self.block(self._result)
      
      if self.model:
        results = []
        model = self.model
        for row in self._result:
          self.vals = row
          obj = model.init_with_coder(self)
          results.append(obj)
          
        if self.retrieval == 'first':
          return results[0]
        else:
          return results
        
      else:
        return self._result
      
    
      
