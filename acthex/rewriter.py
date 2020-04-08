import hexlite.rewriter
from hexlite.ast import shallowparser as shp
import hexlite.auxiliary as aux

import logging, pprint

class ProgramRewriter(hexlite.rewriter.ProgramRewriter):
    def __init__(self, pcontext, shallowprogram, plugins, config):
        # rewrite shallowprogram:
        # * heads that are actions become auxiliary atoms AUXACTION(actionname,c(arguments),prio,cbp)
        # then init original rewriter
        newshallowprogram = self.__rewriteActionsToAuxiliaries(shallowprogram)
        hexlite.rewriter.ProgramRewriter.__init__(self, pcontext, newshallowprogram, plugins, config)

    def __rewriteActionsToAuxiliaries(self, acthexprogram):
        hexprogram = []
        for stm in acthexprogram:
            if __debug__:
                dbgstm = pprint.pformat(stm, width=1000)
                logging.debug('rATA stm='+dbgstm)
            assert(isinstance(stm,shp.alist))
            if stm.left == None:
                candidate = stm[0]
                if any([x == '@' for x in candidate]):
                    newhead = self.__rewriteHead(candidate)
                    stm[0] = newhead
                #if stm.sep == None:
                #    # (disjunctive) fact, processing instruction
                #elif stm.sep == ':-':
                #    # rule
            hexprogram.append(stm)
        return hexprogram

    def __rewriteHead(self, candidate):
        # need to rewrite
        if any([x for x in candidate if x in ['v', '|', ';', ':']]):
            raise Exception("disjunction for acthex action heads not implemented: "+shp.shallowprint(candidate))
        # rewrite one head action
        if len(candidate) not in [2,3,4]:
            raise Exception("unexpected action: "+shp.shallowprint(candidate))

        # "parse"
        actname = candidate[1]
        arguments = None
        modifiers = None
        at = 2
        if len(candidate) > 2:
            if candidate[2].left == '(':
                # arguments (might be omitted)
                arguments = candidate[2]
                at = 3
        if len(candidate) > at:
            # modifiers (for example {1})
            assert(candidate[at].left == '{')
            modifiers = candidate[at]
        if __debug__:
            logging.debug('rH found action name={} arguments={} modifiers={}'.format(repr(actname), repr(arguments), repr(modifiers)))

        # build replacement atom
        actAuxPred = aux.predActhexAction(actname)
        actAuxArgs = shp.alist(left='(', right=')', sep=',')
        if arguments:
            actAuxArgs += [['c', arguments]]
        else:
            actAuxArgs += ['c']
        if modifiers:
            if len(modifiers) > 1 and any([x for x in modifiers if hexlite.flatten(x)[0] in ['b','c','p']]):
                raise Exception("action modifiers: only priority implemented: "+shp.shallowprint(candidate))
            actAuxArgs += modifiers
        else:
          # default priority modifier = {0}
          actAuxArgs += [0]
        relAuxAtom = [ actAuxPred, actAuxArgs ]
        if __debug__:
            logging.debug('rH action replacement head='+pprint.pformat(relAuxAtom, width=1000))

        # return new head
        return relAuxAtom
