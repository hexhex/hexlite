import hexlite.rewriter

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
            hexprogram.append(stm)
        return hexprogram
