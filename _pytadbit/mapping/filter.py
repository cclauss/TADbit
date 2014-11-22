"""
17 nov. 2014


"""
from pytadbit.mapping.restriction_enzymes import count_re_fragments


def apply_filter(fnam, outfile, masked, filters=None):
    """
    """
    masked_reads = set()
    filters = filters or masked.keys()
    for filt in filters:
        masked_reads.update(masked[filt])
    out = open(outfile, 'w')
    for line in open(fnam):
        read = line.split('\t', 1)[0]
        if read not in masked_reads:
            out.write(line)
    out.close()


def filter_reads(fnam, max_molecule_length=500,
                 over_represented=0.005, max_frag_size=100000,
                 min_frag_size=100, re_proximity=5, verbose=True):
    """
    Apply different filters on pair of reads:
       1- self-circle        : reads are comming from a single RE fragment and
          point to the outside (----<===---===>---)
       2- dangling-end       : reads are comming from a single RE fragment and
          point to the inside (----===>---<===---)
       3- extra dangling-end : reads are comming from different RE fragment but
          are close enough (< max_molecule length) and point to the inside
       4- error              : reads are comming from a single RE fragment and
          point in the same direction
       5- duplicated         : the combination of the start positions of the
          reads is repeated -> PCR artifact
       6- too close from RE  : start position of one of the read is too close (
          5 bp by default) from RE cutting site. Non-canonical enzyme activity
          or random physical breakage of the chromatin.
       7- too short          : remove reads comming from small restriction less
          than 100 bp (default) because they are comparable to the read length
       8- too large          : remove reads comming from large restriction
          fragments (default: 100 Kb, P < 10-5 to occur in a randomized genome)
          as they likely represent poorly assembled or repeated regions
       9- over-represented   : reads coming from the top 0.5% most frequently
          detected restriction fragments, they may be prone to PCR artifacts or
          represent fragile regions of the genome or genome assembly errors
    
    :param fnam: path to file containing the pair of reads in tsv format, file
       generated by :func:`pytadbit.mapping.mapper.get_intersection`
    :param 500 max_molecule_length:
    :param 0.005 over_represented:
    :param 100000 max_frag_size:
    :param 100 min_frag_size:
    :param 5 re_proximity:

    :return: dicitonary with, as keys, the kind of filter applied, and as values
       a set of read IDs to be removed
    """
    masked = {1: {'name': 'self-circle'       , 'reads': set()}, 
              2: {'name': 'dangling-end'      , 'reads': set()},
              3: {'name': 'extra dangling-end', 'reads': set()},
              4: {'name': 'error'             , 'reads': set()},
              5: {'name': 'duplicated'        , 'reads': set()},
              6: {'name': 'too close from RE' , 'reads': set()},
              7: {'name': 'too short'         , 'reads': set()},
              8: {'name': 'too large'         , 'reads': set()},
              9: {'name': 'over-represented'  , 'reads': set()}}
    uniq_check = {}
    frag_count = count_re_fragments(fnam)
    num_frags = len(frag_count)
    cut = int((1 - over_represented) * num_frags + 0.5)
    cut = sorted([frag_count[crm] for crm in frag_count])[cut]

    for line in open(fnam):
        read, cr1, ps1, sd1, _, rs1, re1, cr2, ps2, sd2, _, rs2, re2 = line.split()
        uniq_key = tuple(sorted((cr1 + ps1, cr2 + ps2)))
        if not uniq_key in uniq_check:
            uniq_check[uniq_key] = read
        else:
            masked[5]["reads"].add(read)
            if not uniq_check[uniq_key] in masked[5]["reads"]:
                masked[5]["reads"].add(uniq_check[uniq_key])
        ps1, ps2, sd1, sd2, re1, rs1, re2, rs2 = map(int, (
            ps1, ps2, sd1, sd2, re1, rs1, re2, rs2))
        if cr1 != cr2:
            continue
        if re1 == re2:
            if sd1 != sd2:
                if (ps2 > ps1) == sd2:
                    # ----<===---===>---
                    masked[1]["reads"].add(read)
                else:
                    # ----===>---<===---
                    masked[2]["reads"].add(read)
            else:
                # ---===>--===>--- or ---<===--<===---
                masked[4]["reads"].add(read)
        elif (abs(ps1 - ps2) < max_molecule_length
              and ps1 != ps2
              and ps2 > ps1 != sd2):
            # different fragments but facing and very close
            masked[3]["reads"].add(read)
        elif ((abs(re1 - ps1) < re_proximity) or
              (abs(rs1 - ps1) < re_proximity) or 
              (abs(re2 - ps2) < re_proximity) or
              (abs(rs2 - ps2) < re_proximity)):
            masked[6]["reads"].add(read)
        elif ((re1 - rs1) < min_frag_size) or ((re2 - rs2) < min_frag_size) :
            masked[7]["reads"].add(read)
        elif ((re1 - rs1) > max_frag_size) or ((re2 - rs2) > max_frag_size):
            masked[8]["reads"].add(read)
        elif (frag_count.get((cr1, rs1), 0) > cut or
              frag_count.get((cr2, rs2), 0) > cut):
            masked[9]["reads"].add(read)
    del(uniq_check)
    if verbose:
        for k in xrange(1, len(masked) + 1):
            print '%d- %-25s : %d' %(k, masked[k]['name'], len(masked[k]['reads']))
    return masked