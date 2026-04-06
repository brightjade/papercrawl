from ppr.scrapers.acl import SCRAPERS as ACL_SCRAPERS
from ppr.scrapers.aaai import SCRAPERS as AAAI_SCRAPERS
from ppr.scrapers.usenix import SCRAPERS as USENIX_SCRAPERS
from ppr.scrapers.dblp import SCRAPERS as DBLP_SCRAPERS

SCRAPERS = {**ACL_SCRAPERS, **AAAI_SCRAPERS, **USENIX_SCRAPERS, **DBLP_SCRAPERS}
