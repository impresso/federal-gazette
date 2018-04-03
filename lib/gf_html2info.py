#!/usr/bin/python3
"""
Script to produce tab-separated info files from federal web sites.

Each info file contains the following information:
 - Publication date YYYY-MM-DD
 - DOC ID
 - Title
 - Pages
 - Download URL

Example call for processing whole directories
python3 -i indir

example call for processing a single file
python3  < INFILE > OUTPUTFILE
"""

import sys, codecs
import os
from optparse import OptionParser
from lxml import etree


__author__ = "Simon Clematide"
__email__ = "siclemat@cl.uzh.ch"
__organisation__ = "Institute of Computational Linguistics, University of Zurich"
__copyright__ = "UZH, 2018"
__status__ = "development"



sys.stderr = codecs.getwriter('UTF-8')(sys.stderr.buffer)
sys.stdout = codecs.getwriter('UTF-8')(sys.stdout.buffer)
sys.stdin = codecs.getreader('UTF-8')(sys.stdin.buffer)


INFO = [] # list of dictionaries

months_it = {   'gennaio':'01',
        'febbraio':'02',
        'marzo':'03',
        'aprile':'04',
        'maggio':'05',
        'giugno':'06',
        'luglio':'07',
        'agosto':'08',
        'settembre':'09',
        'ottobre':'10',
        'novembre':'11',
        'dicembre':'12'}

months_de = {   'Januar':'01',
        'Februar':'02',
        'März':'03',
        'April':'04',
        'Mai':'05',
        'Juni':'06',
        'Juli':'07',
        'August':'08',
        'September':'09',
        'Oktober':'10',
        'November':'11',
        'Dezember':'12'}

months_fr = {   'janvier':'01',
        'février':'02',
        'mars':'03',
        'avril':'04',
        'mai':'05',
        'juin':'06',
        'juillet':'07',
        'août':'08',
        'septembre':'09',
        'octobre':'10',
        'novembre':'11',
        'décembre':'12'}

# Dictionary for all month names
MONTHS = months_it
MONTHS.update(months_de)
MONTHS.update(months_fr)

def transform_date(date):
    """
    Return YYYY-MM-DD format of textual date

    German dates: <td> 3. März 1849</td>
    French dates: <td> 4 avril 1849</td>
    Italian dates: <td>02 aprile 1971</td>
    """
    date = date.replace('.','').strip().split()
    if len(date) == 3 and date[1] in MONTHS:
        return '%s-%2s-%2s' % (date[2],MONTHS[date[1]].zfill(2),date[0].zfill(2))
    else:
        print('WARNING: malformed date %s' % (date,),file=sys.stderr)


def update_info(path):
    """

    Index contains HTML of  the following form

    </p>
<table class="table table-striped" style="width: 400px">
<tbody>
<tr>
<th>Nr.</th>
<th>Ausgabedatum</th>
<th class="text-right">Seiten</th>
</tr>
<tr><td colspan="3"><strong>Band I</strong></td></tr>
<tr>
<td><a href="/opc/de/federal-gazette/1849/index_1.html">1</a></td>
<td>24. Februar 1849</td>
<td class="nowrap text-right">1&#8211;40</td>
</tr>
<tr>
<td><a href="/opc/de/federal-gazette/1849/index_2.html">2</a></td>
<td>28. Februar 1849</td>
<td class="nowrap text-right">41&#8211;72</td>
</tr>
<tr>

    """
    global INFO
    parser = etree.HTMLParser()
    tree = etree.parse(codecs.open(path,encoding='utf-8'),parser)
    root = tree.getroot()

    for element in root.iter('table',{'class': 'table table-striped'}):
        for tr in element.iter('tr'):
            tds = tr.findall('./td')
            if len(tds) < 3: # jump over th header row
                continue
            else:
                info = {}
                info['subpage'] = tds[0].find('.a').attrib['href']
                info['date'] = transform_date(tds[1].text)
                pagerange = tds[2].text.split('–')
                info['pagestart'] = int(pagerange[0])
                info['pageend'] = int(pagerange[1])
                print(info)


    for element2 in root2.iter('table',{'class': 'table table-striped'}):
        #Extract info box and download links
        infos = str()
        download_links = []
        for td2 in element2.iter('td'):
            for a2 in td2.iter('a'):
                download_links.append(a2.attrib['href'])
                file_name = a2.attrib['href'][-8:]
                for span in a2.iter('span'):
                    l1= span.xpath('text()')
                    l2=span.xpath('b/text()')
                    l=l1[0]+l2[0]+l1[1]
                    l=''.join(l.split())
                    l=file_name+'\t'+l
                    infos+=l

        if td2.text!= None:
            infos+='\t'+td2.text+'\n'

    print(infos)

def main(args,options={}):
    """
    Given a main html index file from www.admin.ch  convert all HTML files to tsv files
    :param input_dir: directory containing tetml files
    :param row_hint: define which Element in the XML tree contains one text row
    :return:
    """
    update_info(args[0])
    exit(0)
    if args.inputFolder:
        xml_files = [f for f in os.listdir(input_dir) if f.endswith('.html')]

        for xml_f in xml_files:

            with open(os.path.join(input_dir, xml_f[:-4] + '.txt'), 'w', encoding='utf-8') as outfile:
                tetml2text(xml_f, outfile, args)
    else:
        tetml2text(sys.stdin, sys.stdout, args)



if __name__ == '__main__':

    parser = OptionParser(
        usage = '%prog [OPTIONS] [ARGS...]',
        version='%prog 0.99', #
        description='Analyze index web files from www.admin.ch for gazette federal and return the relevant information',
        epilog='Contact simon.clematide@uzh.ch'
        )
    parser.add_option('-l', '--logfile', dest='logfilename',
                      help='write log to FILE', metavar='FILE')
    parser.add_option('-q', '--quiet',
                      action='store_true', dest='quiet', default=False,
                      help='do not print status messages to stderr')
    parser.add_option('-d', '--debug',
                      action='store_true', dest='debug', default=False,
                      help='print debug information')

    (options, args) = parser.parse_args()
    if options.debug:
        print >> sys.stderr, "options=",options

    main(args, options)
