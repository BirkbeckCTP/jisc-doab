from .reference_miners import PARSERS, MINERS, FINDERS

def yield_miners(book, input_path):
    for parser in MINERS:
        if parser.can_handle(book, input_path):
            yield parser


def get_parser_by_name(parser):
    for parse_class in PARSERS:
        if parse_class.NAME == parser:
            return parse_class
    import pdb;pdb.set_trace()
    return None


__all__ = PARSERS + FINDERS + MINERS + [yield_miners, get_parser_by_name]
