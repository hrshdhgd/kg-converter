#import csvimport 
import os
from typing import Dict, List, Optional
from collections import defaultdict

from kg_converter.transform_utils.transform import Transform
from kg_converter.utils.transform_utils import parse_header, parse_line, write_node_edge_item

import pandas as pd

"""
Ingest data from the KEGG database

Data of interest:
    1.  Compounds
    2.  Reactions
    3.  Pathways
    4.  KEGG Orthology

"""

class KEGGTransform(Transform):

    def __init__(self, input_dir: str = None, output_dir: str = None, nlp = False) -> None:
        source_name = 'kegg'
        super().__init__(source_name, input_dir, output_dir, nlp)  # set some variables

        self.node_header = ['id', 'name', 'category']
        self.edge_header = ['subject', 'predicate', 'object', 'relation']
        self.nlp = nlp
    
    def run(self, data_file: Optional[str] = None):
        """Method is called and performs needed transformations to process the 
        KEGG data, additional information on this data can be found in the comment 
        at the top of this script.

        :param input_dir: SOurce of the downloaded data from the donwload step.
        :return: None
        
        """

        

        # Pandas DF of 'list' files
        #cpd_list_df = pd.read_csv(self.cpd_list, low_memory=False, sep='\t')
        #path_list_df = pd.read_csv(self.path_list, low_memory=False, sep='\t')
        #rn_list_df = pd.read_csv(self.rn_list, low_memory=False, sep='\t')
        #ko_list_df = pd.read_csv(self.ko_list, low_memory=False, sep='\t')
        #cpd_to_chebi_df = pd.read_csv(self.cpd2chebi, low_memory=False, sep='\t')

        node_dict: dict = defaultdict(int)
        edge_dict: dict = defaultdict(int)

        node_dict, edge_dict = self.post_data(self.path_cpd_link, node_dict, edge_dict, 'w')
        node_dict, edge_dict = self.post_data(self.rn_cpd_link, node_dict, edge_dict, 'a')
        node_dict, edge_dict = self.post_data(self.path_rn_link, node_dict, edge_dict, 'a')
        node_dict, edge_dict = self.post_data(self.path_ko_link, node_dict, edge_dict, 'a')
        node_dict, edge_dict = self.post_data(self.rn_ko_link, node_dict, edge_dict, 'a')
                    

        return None

    def post_data(self, file, seen_node, seen_edge, mode):
        '''
        This function transforms the following KEGG data into nodes and edges:
            -   Pathway <-> Compound
            -   Reaction <-> Compound
            -   Pathways <-> Reaction
            -   Pathway <-> KEGG Orthology
            -   Reaction <-> KEGG Orthology

        :param file: The link file used as input.
        :param seen_node: Dictionary of all nodes recorded to avoid duplication.
        :param seen_edge: Dictionary of all edges recorded to avoid duplication.
        :param mode: Two options ['write' and 'append'] to avoid overwriting of nodes and edges tsv files.
        :return: seen_node and seen_edge such that the nodes and edges are unique throughout the process.
        '''

        with open(file, 'r') as f, \
                open(self.output_node_file, mode) as node, \
                open(self.output_edge_file, mode) as edge:

                # write headers (change default node/edge headers if necessary
                if mode == 'w':
                    node.write('\t'.join(self.node_header) + '\n')
                    edge.write('\t'.join(self.edge_header) + '\n')
                
                seen_node: dict = defaultdict(int)
                seen_edge: dict = defaultdict(int)

                # Nodes
                cpd_node_type = 'biolink:ChemicalSubstance'
                path_node_type = 'biolink:Pathway'
                rn_node_type = 'biolink:MolecularActivity'
                ko_node_type = 'biolink:GeneFamily'

                # Node Prefixes
                cpd_pref = 'KEGG.COMPOUND:'
                rn_pref = 'KEGG.REACTION:'
                path_pref = 'KEGG.PATHWAY:'
                ko_pref = 'KEGG.ORTHOLOGY:'

                # Edges
                path_to_cpd_label = 'biolink:has_participant'
                rn_to_cpd_label = 'biolink:has_participant'
                path_to_rn_label = 'biolink:has_participant'
                path_to_ko_label = 'biolink:has_participant'
                rn_to_ko_label = 'biolink:has_participant'
                predicate = ''
                predicate_curie = ''
                

                path_to_cpd_relation = 'RO:0000057'
                rn_to_cpd_relation = 'RO:0000057'
                path_to_rn_relation = 'RO:0000057'
                path_to_ko_relation = 'RO:0000057'
                rn_to_ko_relation = 'RO:0000057'

                #cpd_to_chebi_df = pd.DataFrame()
                node_id = ''
                node_pref = ''

                header_items = parse_header(f.readline(), sep='\t')

                if all(x in header_items for x in ['cpdId', 'pathwayId']):
                    predicate = path_to_cpd_label
                    predicate_curie = path_to_cpd_relation
                elif all(x in header_items for x in ['cpdId', 'rnId']):
                    predicate = rn_to_cpd_label
                    predicate_curie = rn_to_cpd_relation
                elif all(x in header_items for x in ['pathwayId', 'rnId']):
                    predicate = path_to_rn_label
                    predicate_curie = path_to_rn_relation
                elif all(x in header_items for x in ['koId', 'pathwayId']):
                    predicate = path_to_ko_label
                    predicate_curie = path_to_ko_relation
                elif all(x in header_items for x in ['koId', 'rnId']):
                    predicate = rn_to_ko_label
                    predicate_curie = rn_to_ko_relation
                else:
                    print('Unexpected column names provided.')
                
                for line in f:
                    # transform line into nodes and edges
                    # node.write(this_node1)
                    # node.write(this_node2)
                    # edge.write(this_edge)
                    items_dict = parse_line(line, header_items, sep='\t')
                    
                    edge_id = ''
                    subject = ''
                    object = ''
                    
                    for key in items_dict.keys():
                        list_df = pd.DataFrame()
                        node_type = ''
                        #need_chebi = False
                        if key[:-2] == 'cpd':
                            list_df = pd.read_csv(self.cpd_list, sep='\t', low_memory=False)
                            node_type = cpd_node_type
                            node_pref = cpd_pref
                            #cpd_to_chebi_df = pd.read_csv(self.cpd2chebi, low_memory=False, sep='\t')
                            need_chebi = True
                        elif key[:-2] == 'rn':
                            list_df = pd.read_csv(self.rn_list, sep='\t', low_memory=False)
                            node_type = rn_node_type
                            node_pref = rn_pref
                        elif key[:-2] == 'pathway':
                            list_df = pd.read_csv(self.path_list, sep='\t', low_memory=False)
                            node_type = path_node_type
                            node_pref = path_pref
                        elif key[:-2] == 'ko':
                            list_df = pd.read_csv(self.ko_list, sep='\t', low_memory=False)
                            node_type = ko_node_type
                            node_pref = ko_pref

                        # Get CHEBI equivalent if possible
                        #if need_chebi and (any(cpd_to_chebi_df[key].str.contains(items_dict[key]))):
                            #node_id = cpd_to_chebi_df[cpd_to_chebi_df[key]==items_dict[key]]['chebiId'].values[0]
                        #else:
                        node_id = items_dict[key]


                        if edge_id == '':
                            edge_id = node_id
                            subject = node_pref+node_id
                        else:
                            edge_id += '-'+node_id
                            object = node_pref+node_id
                        
                        #import pdb; pdb.set_trace()

                        if key =='pathwayId':
                            if 'rn' in items_dict[key]:
                                name = list_df[list_df[key] == items_dict[key].replace('rn', 'map')][key[:-2]].values[0]
                            elif 'ko' in items_dict[key]:
                                name = list_df[list_df[key] == items_dict[key].replace('ko', 'map')][key[:-2]].values[0]
                            else:
                                name = list_df[list_df[key] == items_dict[key]][key[:-2]].values[0]

                        else:
                            name = list_df[list_df[key] == items_dict[key]][key[:-2]].values[0]

                        # Nodes
                        if node_id not in seen_node:
                            write_node_edge_item(fh=node,
                                                header=self.node_header,
                                                data=[node_pref+node_id,
                                                      name,
                                                      node_type])
                            seen_node[node_id] += 1
                        

                    # Edges
                    if edge_id not in seen_edge:
                        write_node_edge_item(fh=edge,
                                        header=self.edge_header,
                                        data=[subject,
                                            predicate,
                                            object,
                                            predicate_curie])
                        seen_edge[edge_id] += 1

        return [seen_node, seen_edge]



        





        