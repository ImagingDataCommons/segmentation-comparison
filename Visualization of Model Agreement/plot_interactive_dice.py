import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from google.cloud import bigquery
import google.auth
import sys
import re

if len(sys.argv) != 3:
    print("Usage: python plot_interactive_dice.py <input_csv> <output_html>")
    sys.exit(1)

csv_path = sys.argv[1]
output_path = sys.argv[2]

methods_selected = ['Auto3Dseg', 'Moose', 'MultiTalent', 'OMAS', "TotalSegmentator_1.5", "TotalSegmentator_2.6"]
custom_segment_order =["vertebrae_t2", "vertebrae_t3", "vertebrae_t4", "vertebrae_t5", "vertebrae_t6", "vertebrae_t7", "vertebrae_t8", "vertebrae_t9", "vertebrae_t10"]


palette = {
    "Auto3Dseg": "rgb(255, 127, 14)",
    "Moose": "rgb(44, 160, 44)",
    "MultiTalent": "rgb(214, 39, 40)",
    "TotalSegmentator 1.5": "#80b1d3",
    "TotalSegmentator 2.6": "#08519c",
    "CADS": "#9467BD"
}


method_display_names = {
    "Auto3Dseg": "Auto3Dseg",
    "Moose": "Moose",
    "MultiTalent": "MultiTalent",
    "OMAS": "CADS",
    "TotalSegmentator_1.5": "TotalSegmentator 1.5",
    "TotalSegmentator_2.6": "TotalSegmentator 2.6",
}


df = pd.read_csv(csv_path)


df = pd.read_csv(csv_path)


df = df[df['method'].isin(methods_selected)]
df = df[df['segment'].isin(custom_segment_order)]
df = df[['segment', 'dsc', 'method', 'caseID']].copy()


rev_order = list(reversed(custom_segment_order))
df['segment'] = pd.Categorical(df['segment'], categories=rev_order, ordered=True)
df['segment_numeric'] = df['segment'].cat.codes 

method_order = methods_selected
method_offsets = {m: i * -0.16 for i, m in enumerate(method_order)}

df['segment_offset'] = df['segment_numeric'] + df['method'].map(method_offsets)

df['display_name'] = df['method'].map(method_display_names)

df_mean = df.groupby(['segment', 'method'], as_index=False)['dsc'].mean()
df_mean['segment'] = pd.Categorical(df_mean['segment'], categories=rev_order, ordered=True)
df_mean['segment_numeric'] = df_mean['segment'].cat.codes
df_mean['segment_offset'] = df_mean['segment_numeric'] + df_mean['method'].map(method_offsets)
df_mean['display_name'] = df_mean['method'].map(method_display_names)

credentials, project = google.auth.default()
client = bigquery.Client(credentials=credentials, project="idc-external-031")

query = """
    SELECT 
        main.SeriesInstanceUID AS seg_SeriesInstanceUID, 
        main.StudyInstanceUID,  
        main.SeriesDescription, 
        main.Modality, 
        ref.SeriesInstanceUID AS ct_SeriesInstanceUID 
    FROM `idc-external-031.af_segmentation_benchmarking.18_cases_pilot` AS main,  
    UNNEST(main.ReferencedSeriesSequence) AS ref  
"""
df_bq = client.query(query).to_dataframe()

df_bq["SeriesDescription"] = df_bq["SeriesDescription"].fillna("").astype(str)
df_bq["SeriesDescription_lc"] = df_bq["SeriesDescription"].str.lower()

if "Modality" in df_bq.columns:
    df_bq_seg = df_bq[df_bq["Modality"].astype(str).str.upper().eq("SEG")].copy()
    if df_bq_seg.empty:
        df_bq_seg = df_bq.copy()
else:
    df_bq_seg = df_bq.copy()

study_mapping = (
    df_bq[["ct_SeriesInstanceUID", "StudyInstanceUID"]]
    .drop_duplicates()
    .set_index("ct_SeriesInstanceUID")["StudyInstanceUID"]
)

method_seriesdescription_names = {
    "AUTO3DSEG": ["Auto3DSeg"],
    "MOOSE": ["MOOSE"],
    "MULTITALENT": ["Multitalent"],
    "OMAS": ["OMAS"],
    "TOTALSEGMENTATOR_1.5": ["TotalSegmentator(v1.5.6)"],
    "TOTALSEGMENTATOR_2.6": ["TotalSegmentator-"],
}

def get_seg_uid_for_method(study_id, ct_series_id, method):
    sub = df_bq_seg[
        (df_bq_seg["StudyInstanceUID"] == study_id) &
        (df_bq_seg["ct_SeriesInstanceUID"] == ct_series_id)
    ]
    if sub.empty:
        return ""

    method_u = str(method).upper()
    patterns = method_seriesdescription_names.get(method_u, [])

    for p in patterns:
        p_lc = p.lower()
        hit = sub[sub["SeriesDescription_lc"].str.contains(re.escape(p_lc), na=False)]
        if not hit.empty:
            return hit["seg_SeriesInstanceUID"].iloc[0]

    return sub["seg_SeriesInstanceUID"].iloc[0]

def get_all_segmentations(study_id, ct_series_id):
    matching_segs = df_bq[
        (df_bq["StudyInstanceUID"] == study_id) &
        (df_bq["ct_SeriesInstanceUID"] == ct_series_id)
    ]["seg_SeriesInstanceUID"].dropna().tolist()
    return ",".join(matching_segs)

df["studyID"] = df["caseID"].map(study_mapping).fillna("UNKNOWN")
df["initialSegUID"] = df.apply(
    lambda r: get_seg_uid_for_method(r["studyID"], r["caseID"], r["method"]),
    axis=1
)

df["url"] = df.apply(lambda r:
    f"https://segverify-viewer.web.app/viewer?"
    f"StudyInstanceUIDs={r['studyID']}&"
    f"SeriesInstanceUIDs={r['caseID']},{get_all_segmentations(r['studyID'], r['caseID'])}&"
    f"initialSeriesInstanceUID={r['initialSegUID']}&"
    f"dicomweb=us-central1-idc-external-031.cloudfunctions.net/segverify_proxy1",
    axis=1
)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['dsc'],
    y=df['segment_offset'],
    mode='markers',
    marker=dict(size=6, color='rgba(120,120,120,0.5)'),
    hovertemplate=(
        "<b>%{customdata[2]}</b><br>"
        "Segment: %{customdata[0]}<br>"
        "Dice: %{x:.3f}<br>"
        "caseID: %{customdata[1]}<extra></extra>"
    ),
    customdata=df[['segment','caseID','display_name','url']].values,
    showlegend=False,
    name="cases"
))

for method in method_order:
    disp = method_display_names[method]
    sub = df_mean[df_mean['method'] == method]
    if sub.empty:
        continue
    fig.add_trace(go.Scatter(
        x=sub['dsc'],
        y=sub['segment_offset'],
        mode='markers',
        marker=dict(
            size=12,
            color=palette.get(disp, 'grey'),
        ),
        name=disp,
        hovertemplate=(
            f"<b>{disp}</b><br>"
            "Segment: %{customdata[0]}<br>"
            "Mean Dice: %{x:.3f}<extra></extra>"
        ),
        customdata=sub[['segment']].values,
        showlegend=True
    ))

tickvals = list(range(len(rev_order)))
ticktext = rev_order

fig.update_layout(
    width=1600,
    height=890,
    plot_bgcolor="white",
    paper_bgcolor="white",
    legend_title="Segmentation Model",
    margin=dict(l=120, r=60, t=40, b=60)
)

fig.update_xaxes(
    title="Dice Score",
    range=[0.0, 1.0],
    gridcolor="lightgray",
    zeroline=False
)
fig.update_yaxes(
    title="",
    tickmode="array",
    tickvals=tickvals,
    ticktext=ticktext,
    gridcolor="lightgray",
    zeroline=False
)

post_script = """
var gd = document.getElementsByClassName('plotly-graph-div')[0];
if (gd) {
  gd.on('plotly_click', function(ev){
    if (!ev || !ev.points || !ev.points.length) return;
    var p = ev.points[0];
    // Nur die grauen Einzelpunkte haben eine URL in customdata[3]
    if (p.customdata && p.customdata.length > 3 && p.customdata[3]) {
      window.open(p.customdata[3], '_blank');
    }
  });
}
"""

os.makedirs(os.path.dirname(output_path), exist_ok=True)
fig.write_html(output_path, include_plotlyjs=True, full_html=True, post_script=post_script)
print("Interactive Dice Plot saved:", output_path)
