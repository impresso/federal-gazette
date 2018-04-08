#!/usr/bin/python3
"""
Script to produce tab-separated info files from federal web sites.

Each info file contains the following information:
 - Publication date YYYY-MM-DD
 - DOC ID
 - Title
 - Pages
 - Download URL

Algorithm:
 1. Collect for a year the information about each issue. Stored in YEARINFO
 2. Collect for each issue all relevant infos about each articles. Stored in ISSUEINFO. Note that all information about the year is redundantly stored in the ISSUEINFOs.

Example call for processing whole directories
python3 -i indir

example call for processing a single file
python3  < INFILE > OUTPUTFILE
"""

import sys, codecs,re
import os
import pandas as pd
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


OPTIONS = {} # dictionary of options

YEARINFO = [] # list of dictionaries
ISSUEINFO = []

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


def main(args):
    """
    Given a main html index file from www.admin.ch  convert all HTML files to tsv files
    :param input_dir: directory containing tetml files
    :param row_hint: define which Element in the XML tree contains one text row
    :return:
    """
    global YEARINFO
    for a in args:
        update_year_info(a)
        update_issue_info()
        YEARINFO = []
    output_info()



def update_year_info(path):
    """
    Modify the
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
    global YEARINFO
    if OPTIONS.get('debug'): print('#INFO-YEAR-PATH::',path, file=sys.stderr)
    prefix = re.sub(r'^([^/]+).*',r'\1',path)  # extract the path to index.html

    with codecs.open(path,encoding='utf-8') as f:
        tree = etree.parse(f, etree.HTMLParser(encoding='utf-8'))
        root = tree.getroot()
        volume = 'I'

        for element in root.iter('table',{'class': 'table table-striped'}):
            for tr in element.iter('tr'):
                tds = tr.findall('./td')
                if len(tds) < 3: # jump over th header row
                    if len(tds) == 1:
                        vol = tds[0].find('.strong')
                        if vol is not None:
                            volume = transform_volume(vol.text)
                else:
                    info = {'volume_number' : volume}
                    info['volume_language'] = get_lang(path)
                    info['issue_html'] = prefix + tds[0].find('.a').attrib['href']
                    info['issue_number'] =  re.sub(r'.+index_(\d+)\.html',r'\1',info['issue_html'])
                    info['issue_date'] = transform_date(tds[1].text)
                    pagerange = tds[2].text.split('–')
                    info['issue_page_first'] = int(pagerange[0])
                    info['issue_page_last'] = int(pagerange[1])
                    YEARINFO.append(info)


def update_issue_info():
    """
    Update the information about all issues of each year
    """
    if OPTIONS['debug']:
        print(YEARINFO, file=sys.stderr)
    for yinfo in YEARINFO:
#        print(yinfo,file=sys.stderr)
        for issue_info in  next_article(yinfo['issue_html'], yinfo['issue_date']):
            if OPTIONS.get('debug'): print('#INFO-ISSUE::',issue_info, file=sys.stderr)
            issue_info.update(yinfo)
            ISSUEINFO.append(issue_info)


def transform_date(date):
    """
    Return YYYY-MM-DD format of textual date specifications in de, fr, it

    Note: As the names of months are specific to each language, no prior language information is needed.

    German dates: <td> 3. März 1849</td>
    French dates: <td> 4 avril 1849</td>
    Italian dates: <td>02 aprile 1971</td>
    """
    date = date.replace('.','') # normalize German dates
    fields = date.strip().split()
    if len(fields) == 3 and fields[1] in MONTHS:
        return '%s-%2s-%2s' % (fields[2],MONTHS[fields[1]].zfill(2),fields[0].zfill(2))
    else:
        print('WARNING: malformed date %s' % (date,), file=sys.stderr)


def get_lang(path):
    """
    Return iso-2-letter language
    """
    if '/de/' in path: return 'de'
    if '/fr/' in path: return 'fr'
    if '/it/' in path: return 'it'
    print('Warning: no language information in path', path,file=sys.stderr)

def transform_volume(volume):
    return re.sub(r' *(Band|Volume) +','',volume)

def next_article(path, date):
    """

    Date is a string of the form YYYY-MM-DD

Format of Bundesarchiv  entries

<table class="table table-striped">
	<tbody>
		<tr><th>Quelle</th><th>Titel</th></tr>
		<tr>
			<td style="white-space: nowrap;"><a href="http://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10004300" target="_blank"><span style="font-weight: normal">BBl <b>1864</b> I 1</span></a></td>
			<td>Bericht und Antrag der nationalrätlichen Petitionskommission betreffend den Rekurs des Advokaten Karl Conti von Lugano und mehrerer tessinischen Geistlichen gegen den Beschluss des Bundesrats vom 7. September 1863 wegen Ausschliessung der Geistlichen nach</td>
		</tr>
		<tr>
			<td style="white-space: nowrap;"><a href="http://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10004301" target="_blank"><span style="font-weight: normal">BBl <b>1864</b> I 9</span></a></td>
			<td>Aus den Verhandlungen des schweiz. Bundesrates.</td>
		</tr>
		<tr>
			<td style="white-space: nowrap;"><a href="http://www.amtsdruckschriften.bar.admin.ch/viewOrigDoc.do?id=10004302" target="_blank"><span style="font-weight: normal">BBl <b>1864</b> I 18</span></a></td>
			<td>Inserate.</td>
		</tr>
	</tbody>
</table>


Format of Federal


<table class="table table-striped">
    <tbody>
    <tr>
        <th>Quelle</th>
        <th>Titel</th>
        <!--<th>SR-Nummer*</th>-->
        <th class="nowrap">Verantwortliche Stelle</th>
    </tr>

        <tr>
            <td class="nowrap">
                <a href="/opc/de/federal-gazette/2016/4129.pdf" target="_blank">
                    BBl <strong>2016</strong> 4129</a>
                    <br/>
                    <a href='http://intranet.admin.ch/ch/d/ff/2016/4129.doc' class="internal-items" target="_blank">DOC</a>
            </td>
            <td>Bundesbeschluss über die Kredite für die internationale Zusammenarbeit in Bildung, Forschung und Innovation für die Jahre 2013–2016</td>
            <!--
            <td class="nowrap">

            </td>-->
            <td class="small">
SBFI - Staatssekretariat f&#252;r Bildung, Forschung und Innovation            </td>
        </tr>
        <tr>
            <td class="nowrap">
                <a href="/opc/de/federal-gazette/2016/4131.pdf" target="_blank">
                    BBl <strong>2016</strong> 4131</a>
                    <br/>
                    <a href='http://intranet.admin.ch/ch/d/ff/2016/4131.doc' class="internal-items" target="_blank">DOC</a>
            </td>
            <td>Militärische Plangenehmigung betreffend Gemeinde Bäretswil; Altlastensanierung Schiessplatz, Zielgebiet Obis, Hinter Bettswil</td>
            <!--
            <td class="nowrap">

            </td>-->
            <td class="small">
GS-VBS - Generalsekretariat VBS            </td>
        </tr>


    """
    newformatdata = '1999-06-22'
    site = 'https://www.admin.ch'
    if OPTIONS.get('debug'): print('#INFO-OPENING::',path, file=sys.stderr)
    with codecs.open(path,encoding='utf-8') as f:
        tree = etree.parse(f,etree.HTMLParser(encoding='utf-8'))
        root = tree.getroot()
        for element2 in root.iter('table',{'class': 'table table-striped'}):
            #Extract info box and download links

            download_links = []
            for tr in element2.iter('tr'):
                tds = tr.findall('./td')

                if date < newformatdata:

                    if len(tds) == 2: # jump over the header row
                        a = tds[0].find('a')
                        if not a is None:
                            info = {'issue_path':path}
                            info['article_pdf_url'] = a.attrib['href'].replace('http:','https:')
                            info['article_docid'] = info['article_pdf_url'][-8:]
                            info['article_title'] = re.sub(r'\s+',' ',tds[1].text)
                            startpageinfo = a.find('span/b').tail.split()
                            info['article_page_first'] = int(startpageinfo[-1])
                        else:
                            print('Could not find doc url',path,file=sys.stderr)
                        if OPTIONS.get('debug'): print(info, file=sys.stderr)
                        yield info
                else:
                    if len(tds) >= 2: # jump over the header row
                        a = tds[0].find('a')
                        if not a is None:
                            info = {'issue_path':path}
                            info['article_pdf_url'] = site + a.attrib['href'].replace('http:','https:')
                            info['article_docid'] = re.sub(r'.+?(\d+)/(\d+)\.pdf$',r'\1_\2',info['article_pdf_url'])
                            info['article_title'] = re.sub(r'\s+',' ',tds[1].text)
                            startpageinfo = a.find('strong').tail.split()
                            info['article_page_first'] = int(startpageinfo[-1])
                        else:
                            print('Could not find doc url',path,file=sys.stderr)
                        if OPTIONS.get('debug'): print(info, file=sys.stderr)
                        yield info




def output_info():
    if OPTIONS.get('mode').startswith('tsv'):
        header = OPTIONS.get('mode').endswith('h')
        df = pd.DataFrame(ISSUEINFO)
        df.to_csv(sys.stdout,sep="\t",index=False,header=header)
    else:
        for issue_info in sorted(ISSUEINFO,key=lambda x:x['article_docid']):
            print("\t".join(str(issue_info[key]) for key in sorted(issue_info)))




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
    parser.add_option('-m', '--mode',
                      action='store', dest='mode', default='tsvh',type=str,
                      help='output mode tsvh: tsv with header (%default)')

    (options, args) = parser.parse_args()
    OPTIONS.update(vars(options))
    if OPTIONS['debug']:
        print("options=",OPTIONS, file=sys.stderr)

    main(args)
