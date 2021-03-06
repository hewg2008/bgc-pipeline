#!/usr/bin/env python
# David Prihoda
# Convert HMMscan tabular format into internal Domain CSV file format

import argparse
from Bio import SearchIO
import pandas as pd
import numpy as np

SUPPORTED_FORMATS = [
    'proteins2fasta'
]

def domtbl_to_df(domtbl_path, format=None):
    """
    Convert hmmscan tabular format into internal Domain DataFrame format, one protein domain per line
    :param domtbl_path: Path to HMMscan tabular format result file
    :param format: Format of the protein fasta file that was passed into HMMscan (supported: proteins2fasta or None).
    If it was generated by proteins2fasta, we can extract other values from the sequence ID.
    :return: Domain DataFrame, one protein domain per line
    """
    # Read domain matches in all proteins
    queries = SearchIO.parse(domtbl_path, 'hmmscan3-domtab')

    # Extract all matched domain hits
    print('Reading domains...')
    domains = []
    for query in queries:
        query_domains = []
        for hit in query.hits:
            best_index = np.argmin([hsp.evalue for hsp in hit.hsps])
            best_hsp = hit.hsps[best_index]
            pfam_id = hit.accession.split('.')[0]
            query_domains.append({
                'pfam_id': pfam_id,
                'sequence_id': query.id,
                'domain_start': int(best_hsp.hit_start),
                'domain_end': int(best_hsp.hit_end),
                'evalue': float(best_hsp.evalue),
                'bitscore' : float(best_hsp.bitscore)
            })
        domains += sorted(query_domains, key=lambda x: x['domain_start'])

    print('Domain hits total: {}'.format(len(domains)))

    domains = pd.DataFrame(domains)

    fields = ['sequence_id', 'pfam_id','domain_start','domain_end','evalue','bitscore']


    # Use sequence id generated by proteins2fasta.py to get our gene info directly.
    if format == 'proteins2fasta':
        domains['contig_id'] = domains['sequence_id'].apply(lambda s: s.split('|')[0])
        domains['locus_tag'] = domains['sequence_id'].apply(lambda s: s.split('|')[1])
        domains['protein_id'] = domains['sequence_id'].apply(lambda s: s.split('|')[2])
        domains['gene_start'] = domains['sequence_id'].apply(lambda s: normalize_gene_coord(s.split('|')[3].split('-')[0]))
        domains['gene_end'] = domains['sequence_id'].apply(lambda s: normalize_gene_coord(s.split('|')[3].split('-')[1]))
        domains['gene_strand'] = domains['sequence_id'].apply(lambda s: s.split('|')[4])
        fields = ['contig_id', 'locus_tag', 'protein_id','gene_start','gene_end','gene_strand', 'pfam_id','domain_start','domain_end','evalue','bitscore']
    elif format is None:
        pass
    else:
        raise AttributeError('Format {} not supported, use one of {} or define the protein file.'.format(format, SUPPORTED_FORMATS))
    domains = domains[fields]

    return domains

def normalize_gene_coord(gene_coord):
    """
    Normalize imprecise gene coordinates, will convert <0 into 0 and >1234 into 1234.
    :param gene_coord: Gene coordinate as int or str
    :return: normalized numeric gene coordinate
    """
    if isinstance(gene_coord, int):
        return gene_coord
    if isinstance(gene_coord, str):
        # TODO: Can we turn <0 into 0 and >1234 into 1234?
        if gene_coord.startswith('<') or gene_coord.startswith('>'):
            gene_coord = gene_coord[1:]
        if gene_coord.isnumeric():
            return int(gene_coord)
    raise AttributeError('Invalid gene coord {} ({})'.format(gene_coord, type(gene_coord)))

if __name__ == "__main__":
    # Parse command line
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input", dest="input", required=True,
                      help="Input hmmscan domtbl file name.", metavar="FILE")
    parser.add_argument("-f", "--format", dest="format", required=False, default=None,
                      help="Use specific sequence ID format to extract gene ID and location (supported: {}).".format(SUPPORTED_FORMATS))
    parser.add_argument("-o", "--output", dest="output", required=True,
                      help="Output csv file name.", metavar="FILE")
    options = parser.parse_args()

    df = domtbl_to_df(options.input, format=options.format)

    df.to_csv(options.output, index=False)

    print('Saved to', options.output)