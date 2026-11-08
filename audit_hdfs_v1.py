#!/usr/bin/env python3
"""HDFS_v1 read-only, chunked audit. Python >=3.9, pandas, numpy."""
import argparse
import ast
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

CANDIDATES = {
    'labels': ['anomaly_label.csv'],
    'matrix': ['Event_occurrence_matrix.csv', 'event_occurrence_matrix.csv'],
    'traces': ['Event_traces.csv', 'event_traces.csv'],
    'templates': ['HDFS.log_templates.csv', 'HDFS_templates.csv', 'HDFS.log_templates.csv'],
}

def native(x):
    if isinstance(x, dict): return {str(k): native(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [native(v) for v in x]
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return float(x) if np.isfinite(x) else None
    if isinstance(x, float) and not math.isfinite(x): return None
    return x

def resolve(folder, names):
    for name in names:
        p = folder / name
        if p.is_file(): return p
    for p in folder.glob('*.csv'):
        if p.name.lower() in {x.lower() for x in names}: return p
    return None

def is_blank(s):
    return s.isna() | s.astype('string').str.strip().eq('').fillna(True)

def init_file(p):
    cols = pd.read_csv(p, nrows=0, encoding='utf-8-sig').columns.tolist()
    return {'file':p.name, 'size_mb':round(p.stat().st_size/1048576,2), 'columns':cols,
            'rows':0, 'missing':Counter(), 'examples':{}, 'duplicate_blockids':0,
            'unique_blockids':0, 'blank_blockids':0}

def read_chunks(p, size):
    return pd.read_csv(p, chunksize=size, dtype='string', encoding='utf-8-sig',
                       keep_default_na=True, low_memory=False, on_bad_lines='warn')

def count_rows_and_missing(res, chunk):
    res['rows'] += len(chunk)
    for c in chunk.columns:
        res['missing'][c] += int(is_blank(chunk[c]).sum())

def safe_numeric(series):
    return pd.to_numeric(series, errors='coerce')

def audit_labels(p, size):
    res = init_file(p); counts=Counter(); ids=set(); labels_by_id={}; conflicting=0; duplicates=0
    for ch in read_chunks(p,size):
        count_rows_and_missing(res,ch)
        if not {'BlockId','Label'}.issubset(ch.columns):
            res['error']='Expected BlockId and Label columns'; break
        for bid,lab in zip(ch['BlockId'].fillna('').str.strip(),ch['Label'].fillna('').str.strip()):
            counts[lab if lab else '<BLANK>']+=1
            if not bid: res['blank_blockids']+=1; continue
            if bid in ids:
                duplicates+=1
                if labels_by_id[bid]!=lab: conflicting+=1
            else: ids.add(bid); labels_by_id[bid]=lab
    res['label_counts']=dict(counts); res['duplicate_blockids']=duplicates
    res['conflicting_duplicate_labels']=conflicting; res['unique_blockids']=len(ids)
    return res,labels_by_id

def audit_matrix(p,size,truth):
    res=init_file(p); ids=set(); seen=Counter(); type_ct=Counter(); raw_label_ct=Counter()
    joined=Counter(); mismatch=Counter(); label_assoc=Counter(); type_assoc=Counter()
    ev_cols=[c for c in res['columns'] if re.fullmatch(r'E\d+',c)]
    res['event_column_count']=len(ev_cols)
    res['event_columns_preview']=ev_cols[:12]
    nonnumeric=Counter(); negative=Counter(); event_nonzero=Counter(); event_sum=Counter()
    zero_rows=0; total_counts=0; count_max=0; numeric_cells=0
    for ch in read_chunks(p,size):
        count_rows_and_missing(res,ch)
        if 'BlockId' not in ch:
            res['error']='Missing BlockId'; break
        bids=ch['BlockId'].fillna('').str.strip()
        for bid in bids:
            if not bid: res['blank_blockids']+=1
            elif bid in ids: res['duplicate_blockids']+=1
            else: ids.add(bid)
        types=ch['Type'].fillna('').str.strip() if 'Type' in ch else pd.Series(['']*len(ch),index=ch.index)
        local_labs=ch['Label'].fillna('').str.strip() if 'Label' in ch else pd.Series(['']*len(ch),index=ch.index)
        type_ct.update(types.replace('', '<BLANK>').value_counts().to_dict())
        raw_label_ct.update(local_labs.replace('', '<BLANK>').value_counts().head(30).to_dict())
        for bid,ty,raw in zip(bids,types,local_labs):
            if not bid: continue
            if bid not in truth: mismatch['matrix_not_in_truth']+=1; continue
            target=truth[bid]; joined[target]+=1
            type_assoc[(ty or '<BLANK>',target)]+=1
            label_assoc[('nonempty' if raw else 'empty',target)]+=1
            if ty.lower() in ('success','fail'):
                predicted='Anomaly' if ty.lower()=='fail' else 'Normal'
                if predicted!=target: mismatch['type_vs_truth_disagree']+=1
        if ev_cols:
            num=ch[ev_cols].apply(pd.to_numeric,errors='coerce')
            invalid=(~ch[ev_cols].isna() & num.isna()).sum()
            for c,v in invalid.items(): nonnumeric[c]+=int(v)
            neg=(num<0).sum()
            for c,v in neg.items(): negative[c]+=int(v)
            nz=(num.fillna(0)>0).sum()
            for c,v in nz.items(): event_nonzero[c]+=int(v)
            sums=num.clip(lower=0).sum()
            for c,v in sums.items(): event_sum[c]+=float(v)
            rowtot=num.fillna(0).sum(axis=1)
            zero_rows+=int(rowtot.eq(0).sum())
            total_counts+=float(rowtot.sum())
            count_max=max(count_max,float(rowtot.max()))
            numeric_cells+=len(ch)*len(ev_cols)
    res['unique_blockids']=len(ids)
    res['type_counts']=dict(type_ct);res['matrix_label_top_values']=dict(raw_label_ct)
    res['groundtruth_join_counts']=dict(joined)
    res['join_issues']=dict(mismatch)
    res['type_by_groundtruth']=[{'Type':a,'GroundTruth':b,'count':v} for (a,b),v in type_assoc.items()]
    res['matrix_label_presence_by_groundtruth']=[{'MatrixLabel':a,'GroundTruth':b,'count':v} for (a,b),v in label_assoc.items()]
    res['event_numeric_invalid_total']=sum(nonnumeric.values())
    res['event_numeric_invalid_by_column']=dict(nonnumeric)
    res['event_negative_total']=sum(negative.values())
    res['zero_event_rows']=zero_rows
    res['mean_events_per_block']=round(total_counts/res['rows'],3) if res['rows'] else None
    res['max_events_per_block']=count_max
    res['top_events_by_total_occurrence']=event_sum.most_common(15)
    res['top_events_by_blocks_present']=event_nonzero.most_common(15)
    return res,ids

def parse_trace(val):
    if not isinstance(val,str) or not val.strip(): return None
    try:
        a=ast.literal_eval(val)
        if isinstance(a,(list,tuple)): return [str(x).strip() for x in a]
    except (ValueError,SyntaxError,TypeError,MemoryError,RecursionError): pass
    return re.findall(r'\bE\d+\b',val)

def audit_traces(p,size,truth,matrix_ids):
    res=init_file(p); ids=set(); lengths=Counter(); event_ct=Counter(); missing_truth=0; missing_matrix=0
    bad_traces=0; parsed=0; intervals=Counter(); latencies=Counter(); type_ct=Counter(); label_presence=Counter()
    for ch in read_chunks(p,size):
        count_rows_and_missing(res,ch)
        if 'BlockId' not in ch:
            res['error']='Missing BlockId'; break
        for row in ch.itertuples(index=False,name=None):
            d=dict(zip(ch.columns,row));bid='' if pd.isna(d.get('BlockId')) else str(d.get('BlockId')).strip()
            if bid in ('','<NA>'):res['blank_blockids']+=1;continue
            if bid in ids:res['duplicate_blockids']+=1
            else:ids.add(bid)
            if bid not in truth:missing_truth+=1
            if bid not in matrix_ids:missing_matrix+=1
            seq=parse_trace(d.get('Features'))
            if seq is None:bad_traces+=1
            else:
                parsed+=1;lengths[len(seq)]+=1;event_ct.update(seq)
            ty='' if pd.isna(d.get('Type')) else str(d.get('Type')).strip()
            type_ct[ty if ty not in ('','<NA>') else '<BLANK>']+=1
            lab='' if pd.isna(d.get('Label')) else str(d.get('Label')).strip()
            label_presence['nonempty' if lab not in ('','<NA>') else 'empty']+=1
            for field,counter in [('TimeInterval',intervals),('Latency',latencies)]:
                v=d.get(field)
                if v is not None and not pd.isna(v) and str(v).strip():counter['nonempty']+=1
                else:counter['empty']+=1
    res['unique_blockids']=len(ids);res['missing_in_groundtruth']=missing_truth
    res['missing_in_matrix']=missing_matrix;res['parsed_traces']=parsed;res['unparseable_or_empty_traces']=bad_traces
    res['trace_length_distribution']={'min':min(lengths) if lengths else None,
                                      'max':max(lengths) if lengths else None,
                                      'mean':round(sum(k*v for k,v in lengths.items())/sum(lengths.values()),3) if lengths else None,
                                      'most_common_lengths':lengths.most_common(15)}
    res['top_events_in_traces']=event_ct.most_common(15)
    res['type_counts']=dict(type_ct);res['trace_label_presence']=dict(label_presence)
    res['TimeInterval_presence']=dict(intervals);res['Latency_presence']=dict(latencies)
    return res,ids

def audit_templates(p,size):
    res=init_file(p); ids=set(); duplicates=0
    for ch in read_chunks(p,size):
        count_rows_and_missing(res,ch)
        if 'EventId' in ch:
            for ev in ch['EventId'].fillna('').str.strip():
                if ev in ids:duplicates+=1
                elif ev:ids.add(ev)
    res['unique_eventids']=len(ids);res['duplicate_eventids']=duplicates
    res['event_ids_preview']=sorted(ids,key=lambda x:(len(x),x))[:12]
    return res,ids

def markdown(data):
    lines=['# Audit HDFS_v1 — rapport de données','',f"Généré le : {data['generated_utc']}",'',
           f"Dossier source : `{data['input_dir']}`",'',
           '**Confidentialité :** statistiques agrégées uniquement, aucun log brut ni identifiant de bloc exporté.','',
           '## Fichiers détectés','', '| Catégorie | Fichier | Taille (Mo) | Lignes |', '|---|---|---:|---:|']
    for k,v in data['files'].items():
        lines.append(f"| {k} | {v.get('file','Absent')} | {v.get('size_mb','—')} | {v.get('rows','—')} |")
    lines+=['','## Alertes et vérifications','']
    if data['warnings']:
        lines += ['- '+x for x in data['warnings']]
    else: lines+=['- Aucune alerte automatique détectée (cela ne garantit pas l’absence de fuite de données).']
    for k,v in data['files'].items():
        lines+=['',f'## {k}','',f"**Colonnes :** {', '.join(v.get('columns',[])) or '—'}",'',
                f"**Valeurs manquantes :** `{json.dumps(v.get('missing',{}),ensure_ascii=False)}`",'']
        for field,value in v.items():
            if field in ('file','size_mb','columns','rows','missing','examples'):continue
            lines.append(f"**{field} :** `{json.dumps(value,ensure_ascii=False)}`")
            lines.append('')
    lines+=['## Prochaines décisions','',
            '1. Confirmer la colonne cible officielle via `anomaly_label.csv`.','2. Exclure `Type` et `Label` de la matrice des features avant tout entraînement.','3. Vérifier les correspondances de BlockId et la présence d’événements inconnus.','4. Définir une stratégie de split adaptée (pas de chronologie supposée).','5. Garder le test final isolé de la sélection des modèles.','']
    return '\n'.join(lines)

def main():
    ap=argparse.ArgumentParser(description='Audit HDFS_v1 chunked, read-only')
    ap.add_argument('--data-dir',type=Path,default=Path('data/raw/preprocessed'))
    ap.add_argument('--output-dir',type=Path,default=Path('reports/data_audit'))
    ap.add_argument('--chunk-size',type=int,default=10000)
    args=ap.parse_args()
    if args.chunk_size<1:ap.error('--chunk-size must be >= 1')
    folder=args.data_dir.resolve();out=args.output_dir.resolve()
    if not folder.is_dir():ap.error(f'Dossier introuvable : {folder}')
    out.mkdir(parents=True,exist_ok=True)
    data={'generated_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
          'input_dir':str(folder),'files':{},'warnings':[]}
    paths={k:resolve(folder,v) for k,v in CANDIDATES.items()}
    for k,p in paths.items():
        if p is None:data['warnings'].append(f'Fichier {k} absent (noms attendus : {CANDIDATES[k]})')
    truth={};matrix_ids=set()
    if paths['labels']:
        print('[1/4] Labels...');data['files']['labels'],truth=audit_labels(paths['labels'],args.chunk_size)
        r=data['files']['labels']; counts=r.get('label_counts',{})
        if set(counts)-{'Normal','Anomaly'}:data['warnings'].append('Valeurs inattendues dans anomaly_label.csv : '+str(sorted(set(counts)-{'Normal','Anomaly'})))
        if r.get('conflicting_duplicate_labels'):data['warnings'].append('BlockId avec étiquettes contradictoires dans anomaly_label.csv')
        n=sum(counts.values());a=counts.get('Anomaly',0)
        r['anomaly_rate_pct']=round(100*a/n,4) if n else None
    if paths['matrix']:
        print('[2/4] Matrice événements...');data['files']['matrix'],matrix_ids=audit_matrix(paths['matrix'],args.chunk_size,truth)
        r=data['files']['matrix']
        if 'Type' in r['columns']:data['warnings'].append('Risque de fuite de cible : Type (Success/Fail) dans la matrice. À EXCLURE des features.')
        if 'Label' in r['columns']:data['warnings'].append('Risque de fuite de cible : Label de la matrice. À EXCLURE des features.')
        if r.get('event_numeric_invalid_total'):data['warnings'].append('Valeurs non numériques détectées dans les colonnes E*.')
        if r.get('event_negative_total'):data['warnings'].append('Fréquences d’événements négatives détectées.')
        if truth:
            missing=len(set(truth)-matrix_ids);r['groundtruth_blockids_missing_in_matrix']=missing
            if missing:data['warnings'].append(f'{missing} BlockId du ground truth absents de la matrice.')
    if paths['traces']:
        print('[3/4] Traces...');data['files']['traces'],trace_ids=audit_traces(paths['traces'],args.chunk_size,truth,matrix_ids)
        if truth:
            data['files']['traces']['groundtruth_blockids_missing_in_traces']=len(set(truth)-trace_ids)
    if paths['templates']:
        print('[4/4] Templates...');data['files']['templates'],template_ids=audit_templates(paths['templates'],args.chunk_size)
        if 'matrix' in data['files']:
            event_cols=set(c for c in data['files']['matrix']['columns'] if re.fullmatch(r'E\d+',c))
            data['files']['matrix']['event_columns_without_template']=sorted(event_cols-template_ids)
            if event_cols-template_ids:data['warnings'].append('Certaines colonnes événements ne sont pas présentes dans les templates.')
    for k,v in data['files'].items():
        if v.get('duplicate_blockids'):data['warnings'].append(f"{k}: {v['duplicate_blockids']} BlockId dupliqués.")
    data=native(data)
    json_path=out/'hdfs_data_report.json';md_path=out/'hdfs_data_report.md'
    json_path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    md_path.write_text(markdown(data),encoding='utf-8')
    print('\nAudit terminé :')
    print(' -',md_path)
    print(' -',json_path)
    print('Aucune donnée source modifiée.')

if __name__=='__main__':
    main()
