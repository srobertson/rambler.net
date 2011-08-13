import cStringIO
REGULAR_EXPRESSION_CHARS='.*+?'
IGNORE_CHARS='()'

def compareExpressions(exp1,exp2):
    """Given two strings which represent regular expressions returns compare how greedy an expressin 
    -1 if exp1 is more precicse than than exp2
    0 if exp1 is as precise as exp2
    1 if exp1 is less precise than exp2

    This function is useful when you want to test a string against a series of regular expressions 
    and you want more precises expressions to have a chance at evaluating a string. 

    For examlpe consider the following regular expressions
    >>> expressions = ['.*', 'foo.*']

    If we were to evaluate a string against each expression and stop
    on the first match like this code
    
    >>> import re 
    >>> for expr in expressions:
    ...   if re.match(expr, 'foo'):
    ...     break

    The second expression 'foo.*' would never be tested because '.*'
    matches everything.

    >>> expr == '.*'
    True

    Therefore we want the more specific match to run first, which
    means we need to sort the list.

    >>> expressions.sort(compareExpressions)
    >>> expressions
    ['foo.*', '.*']
    
    """
    
    # We delibertly flip exp2 and exp1 when calling cmp() because we
    # want higher precision expressions to come first, not last.
    return cmp(expressionPrecision(exp2), expressionPrecision(exp1))

def expressionPrecision(expStr):
    """ Return the precision of an expression. The precision is simply the
    number of non regular expression characters from the begining of the
    string before reaching the first character that is part of a regular
    expression.

    For example
    
    >>> expressionPrecision('blah')
    4

    Because 'blah' contains no regular expression characters

    This next examlpe the precision is 2 because the expresion can
    match either "blah", "bloh", "blue herring"

    >>> expressionPrecision('bl(.*)h')
    2

    Now in this example the precision is three because the grouping
    character has no impact on the  precission of the expression. 

    >>> expressionPrecision('bl(a.*)h')
    3
    
    Escaped regulare expression characters should count as normal characters
    >>> expressionPrecision('blah\.')
    5
    """

    
    stream = cStringIO.StringIO(expStr)

    precision = 0
    char = stream.read(1)
    while char:
	if char == '\\': # Skip over the next character and raise the precision
	    char = stream.read(1)
	    precision += 1
	elif char in IGNORE_CHARS:
	    # It's a ( or something else that has no impacto on the
	    # precision of the string.
	    pass

	elif char not in REGULAR_EXPRESSION_CHARS:
	    precision += 1
	else:
	    # We found a regular expression character, return the precission
	    break
	char = stream.read(1)

    return precision


if __name__ == "__main__":
    import sys, doctest
    mod = sys.modules[__name__]
    doctest.testmod(mod)

