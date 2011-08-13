from pyparsing import Literal, OneOrMore, QuotedString, SkipTo, stringEnd


"""Givent a string, this parser skips to the starting charcters '<%',
returning everything it skips over as a token. Everything that is
between '<%=' and '%>' are returned as a token labeled
assignment. This is repeated until we run out of '<%' at which point
we return everything up to the end of a string as a token."""

startExp = Literal('<%')
assignExp = QuotedString('<%=', endQuoteChar='%>', multiline=True)
assignExp = assignExp.setResultsName('assignment')

ERBParser = OneOrMore(SkipTo(startExp) + assignExp) + SkipTo(stringEnd)
ERBParser.leaveWhitespace()

class ERBTemplate(object):
    def loadFromFile(self, fileName):
        tokens = ERBParser.parseFile(fileName)

        # Create a dictionary where the key is the position the token
        # was found and and the value is the token's name as set by setResultsName

        typeByPos  = dict( [ (v[1],k) for (k,vlist) in tokens._ParseResults__tokdict.items()
                             for v in vlist ] )
        self.typeByPos = typeByPos
        self.tokens = tokens

    def render(self, context):
        tokens = self.tokens
        tokenCount = len(tokens)
        
        for i in range(tokenCount):
            token = tokens[i]
            ttype = self.typeByPos.get(i)
            if ttype == 'assignment':
                yield str(eval(token,{},context))
            else:
                yield token
            

if __name__ == "__main__":
    import sys
    f = open(sys.argv[1])

    t = ERBTemplate()
    t.loadFromFile(f)
    
    value = 100
    title = "Hoo ya"
    results = ""
    for line in t.render(locals()):
        results += line

    print results
    assert results == "<html><body><h1>Hoo ya</h1>Ya the value is 100</body></html>"
