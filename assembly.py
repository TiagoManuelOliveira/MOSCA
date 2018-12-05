# -*- coding: utf-8 -*-
"""
MOSCA's Assembly package for performing Assembly with MetaSPAdes
and Megahit and Quality Control analysis of the resulting contigs

By João Sequeira

Jun 2017
"""

import subprocess, os
from mosca_tools import MoscaTools

mtools = MoscaTools()

class Assembler:
    
    def __init__ (self, **kwargs):
        self.__dict__ = kwargs
        
    def set_argument(self, x):
        if isinstance(self.__dict__[x], str): 
            return ' --' + x.replace('_','-') + ' ' + self.__dict__[x]
        elif isinstance(self.__dict__[x], list): 
            result = ' --' + x.replace('_','-') + ' '
            for part in self.__dict__[x]:
                result += self.__dict__[x] + ','
            return result.rstrip(',')
        elif self.__dict__[x] == True:
            return ' --' + x.replace('_','-')
        return 'Not a valid argument'
        
    def metaspades_command(self):
        assembler = self.__dict__.pop('assembler')
        result = 'python ' + os.path.expanduser('~/SPAdes-3.11.1-Linux/bin/metaspades.py')
        result += ' -o ' + self.out_dir + '/Assembly/' + self.name
        out_dir = self.__dict__.pop('out_dir')
        forward, reverse = self.forward, self.reverse
        name = self.__dict__.pop('name')
        # Input data
        if hasattr(self, 'interleaved'):
            result += ' --12 ' + self.interleaved
        if hasattr(self, 'forward'):
            result += ' -1 ' + self.forward
        if hasattr(self, 'reverse'):
            result += ' -2 ' + self.reverse
        if hasattr(self, 'unpaired'):
            result += ' -s ' + self.unpaired
        data_types = {'files_paired':'-12','forward':'-1','reverse':'-2',
                      'unpaired':'-s','orientation':'-'}
        if hasattr(self, 'pe_libraries'):
            for library, data in self.pe_libraries.items():
                result += ' --pe' + library + data_types[data[0]]
                if data[0] != 'orientation':
                    result += ' '
                result += data[1]
        if hasattr(self, 'se_libraries'):
            for library, data in self.se_libraries.items():
                result += ' --s' + library + ' ' + data[1]
        for attr in ['interleaved', 'forward', 'reverse', 'unpaired']:
            if hasattr(self, attr):
                self.__dict__.pop(attr)
        for arg in self.__dict__.keys():
            result += self.set_argument(arg)
        self.out_dir = out_dir
        self.assembler = assembler
        self.forward, self.reverse = forward, reverse
        self.name = name
        return result
    
    def megahit_command(self):
        assembler = self.__dict__.pop('assembler')
        result = os.path.expanduser('~/megahit/megahit -f')
        if hasattr(self, 'forward') and hasattr(self, 'reverse'):
            result += ' -1 ' + self.forward + ' -2 ' + self.reverse
            self.__dict__.pop('forward'); self.__dict__.pop('reverse')
        if hasattr(self, 'interleaved'):
            result += ' --12 '
            for file in self.files_paired:
                result += file + ','
            result.rstrip(',')
            self.__dict__.pop('interleaved')
            
        for arg in self.__dict__.keys():
            result += self.set_argument(arg)
        self.__dict__['assembler'] = assembler
        return result
    
    def run_assembler(self):
        if self.assembler == 'metaspades':
            bashCommand = self.metaspades_command()
        elif self.assembler == 'megahit':
            bashCommand = self.megahit_command()
        mtools.run_command(bashCommand)
    
    def bowtie2(self, reads, contigs, temp, sam, log):
        bashCommand = 'bowtie2-build ' + contigs + ' ' + temp
        mtools.run_command(bashCommand)
        bashCommand = 'bowtie2 -a -x ' + temp + ' -q -1 ' + reads[0] + ' -2 ' + reads[1]
        bashCommand = bashCommand.rstrip(',') + ' -p 6 1> ' + sam + ' 2> ' + log
        mtools.run_command(bashCommand)
        return self.parse_bowtie2(log)
        
    def parse_bowtie2(self, file):
        handler = open(file)
        lines = handler.readlines()
        return lines[-1].split('%')[0]
    
    def metaquast(self, contigs, out_dir):
        bashCommand = 'metaquast.py --threads 6 --output-dir ' + out_dir + ' ' + contigs
        mtools.run_command(bashCommand)
     
    def quality_control(self):
        terminations = {'megahit':'/final.contigs.fa', 'metaspades':'/contigs.fasta'}
        out_dir = self.out_dir + '/Assembly/' + self.name
        contigs = out_dir + terminations[self.assembler]
        self.metaquast(contigs, out_dir + '/quality_control')
        percentage_of_reads = self.bowtie2([self.forward,self.reverse], contigs, 
                                           out_dir + '/quality_control', 
                                           out_dir + '/quality_control/library.sam', 
                                           out_dir + '/quality_control/bowtie.log')
        
        if os.path.isfile(out_dir + '/quality_control/combined_reference/report.tsv'):
            os.rename(out_dir + '/quality_control/combined_reference/report.tsv', 
                      out_dir + '/quality_control/report.tsv')
        
        handler = open(out_dir + '/quality_control/report.tsv', 'a')
        handler.write('Reads aligned (%)\t' + percentage_of_reads + '\n')
        
    def make_contigs_gff(self, file):
        pass
        
    def run(self):
        self.run_assembler()
        self.quality_control()

if __name__ == '__main__':
    
    for name in ['EST6_S1_L001','OLDES6_S4_L001']:
    
        assembler = Assembler(out_dir = 'MGMP',
                              assembler = 'metaspades',
                              forward = 'MGMP/Preprocess/Trimmomatic/quality_trimmed_' + name + '_forward_paired.fq',
                              reverse = 'MGMP/Preprocess/Trimmomatic/quality_trimmed_' + name + '_reverse_paired.fq',
                              name = name)
        
        assembler.run()
    
    