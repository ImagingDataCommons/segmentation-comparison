import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
import google.auth
import os
import sys
import re

if len(sys.argv) != 3:
    print(
        "Usage: python interactive_volume_plot.py "
        "<segmentation_volumes.csv> <output_dir>"
    )
    sys.exit(1)

csv_path = sys.argv[1]
output_dir = sys.argv[2]
df = pd.read_csv(csv_path)

custom_segment_groups = [
    ("lung", ["lung_upper_lobe_left", "lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_left", "lung_lower_lobe_right"]),
    ("heart", ["heart"]),
    ("sternum", ["sternum"]),
    ("ribs_3-6", ["rib_left_3", "rib_right_3", "rib_left_4", "rib_right_4","rib_left_5", "rib_right_5", "rib_left_6", "rib_right_6"]),
    ("Vertebrae_T_2-10", ["vertebrae_T2", "vertebrae_T3", "vertebrae_T4", "vertebrae_T5", "vertebrae_T6", "vertebrae_T7", "vertebrae_T8", "vertebrae_T9", "vertebrae_T10"]),
]

symbols_group = [
    "circle", "square", "diamond", "cross",
    "x", "star", "triangle-up", "triangle-down", "hexagon2"
]


df_wide = df.pivot_table(index=["caseID", "segment"], columns="method", values="volume").reset_index()
df_wide = df_wide.rename(columns={"Overlap": "OverlapVolume"})
normal_methods = [col for col in df_wide.columns if col not in ["caseID", "segment", "OverlapVolume"]]

df_long = pd.melt(
    df_wide,
    id_vars=["caseID", "segment", "OverlapVolume"],
    value_vars=normal_methods,
    var_name="method",
    value_name="ModelVolume"
)
#df_long = df_long[~df_long["method"].isin(["TS_1.5", "OMAS", "Moose", "MOOSE", "MultiTalent"])]

df_long = df_long.drop_duplicates(
    subset=["caseID", "segment", "method", "ModelVolume", "OverlapVolume"]
)

all_segments = set(seg for _, seg_list in custom_segment_groups for seg in seg_list)
df_long = df_long[df_long["segment"].isin(all_segments)].copy()

df_long["OverlapPercent"] = df_long["OverlapVolume"] / df_long["ModelVolume"] * 100
df_long["ModelVolume"] = df_long["ModelVolume"] / 1000  # 1 mL = 1000 mm³
df_long["method"] = df_long["method"].str.upper()

method_display_names = {
    "AUTO3DSEG": "Auto3Dseg",
    "MOOSE": "Moose",
    "MULTITALENT": "MultiTalent",
    "OMAS": "CADS",
    "TS_1.5": "TotalSegmentator 1.5",
    "TS_2.6": "TotalSegmentator 2.6"
}
df_long["method_display"] = df_long["method"].map(method_display_names)

custom_palette = {
    "Auto3Dseg": "rgb(255, 127, 14)",
    "Moose": "rgb(44, 160, 44)",
    "MultiTalent": "rgb(214, 39, 40)",
    "TotalSegmentator 1.5": "#80b1d3",
    "TotalSegmentator 2.6": "#08519c",
    "CADS": "#9467BD"
}

method_seriesdescription_names = {
    "AUTO3DSEG": ["Auto3DSeg"],
    "MOOSE": ["MOOSE"],
    "MULTITALENT": ["Multitalent"],
    "OMAS": ["OMAS"],
    "TS_1.5": ["TotalSegmentator(v1.5.6)"],
    "TS_2.6": ["TotalSegmentator-"],
}

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
print(df_bq.columns)

df_bq["SeriesDescription"] = df_bq["SeriesDescription"].fillna("").astype(str)
df_bq["SeriesDescription_lc"] = df_bq["SeriesDescription"].str.lower()

if "Modality" in df_bq.columns:
    df_bq_seg = df_bq[df_bq["Modality"].astype(str).str.upper().eq("SEG")].copy()
    if df_bq_seg.empty:
        df_bq_seg = df_bq.copy()
else:
    df_bq_seg = df_bq.copy()

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

if "studyID" not in df_long.columns:
    study_mapping = (
        df_bq[["ct_SeriesInstanceUID", "StudyInstanceUID"]]
        .drop_duplicates()
        .set_index("ct_SeriesInstanceUID")["StudyInstanceUID"]
    )
    df_long["studyID"] = df_long["caseID"].map(study_mapping).fillna("UNKNOWN")

df_long["initialSegUID"] = df_long.apply(
    lambda row: get_seg_uid_for_method(row["studyID"], row["caseID"], row["method"]),
    axis=1
)

df_long["url"] = df_long.apply(lambda row:
    f"https://segverify-viewer.web.app/viewer?"
    f"StudyInstanceUIDs={row['studyID']}&"
    f"SeriesInstanceUIDs={row['caseID']},{get_all_segmentations(row['studyID'], row['caseID'])}&"
    f"initialSeriesInstanceUID={row['initialSegUID']}&"
    f"dicomweb=us-central1-idc-external-031.cloudfunctions.net/segverify_proxy1",
    axis=1)

os.makedirs(output_dir, exist_ok=True)

for group_name, seg_list in custom_segment_groups:
    group_df = df_long[df_long["segment"].isin(seg_list)].copy()
    if group_df.empty:
        print(f"No data for group '{group_name}' with segments: {seg_list}")
        continue

    group_symbols = {seg: symbols_group[i % len(symbols_group)] for i, seg in enumerate(seg_list)}

    min_val_x = group_df["ModelVolume"].min()
    max_val_x = group_df["ModelVolume"].max()

    fig = go.Figure()

    zones = [
        (100, 90, 'rgba(0, 128, 0, 0.15)', '≤100–90%'),
        (90, 75, 'rgba(255, 165, 0, 0.2)', '≤90–75%'),
        (75, 50, 'rgba(255, 0, 0, 0.15)', '≤75–50%'),
        (50, 25, 'rgba(0, 0, 255, 0.12)', '≤50–25%')
    ]
    for top, bottom, color, _ in zones:
        fig.add_trace(go.Scatter(
            x=[min_val_x, max_val_x, max_val_x, min_val_x],
            y=[top, top, bottom, bottom],
            fill='toself',
            fillcolor=color,
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo='skip',
            showlegend=False
        ))

    fig.add_trace(go.Scatter(
        x=[min_val_x, max_val_x],
        y=[50, 50],
        mode="lines",
        line=dict(color="black", dash="dash", width=2),
        name="50%",
        showlegend=True
    ))

    for (case, segment), group in group_df.groupby(["caseID", "segment"]):
        if len(group) > 1:
            group_sorted = group.sort_values(by="ModelVolume")
            fig.add_trace(go.Scatter(
                x=group_sorted["ModelVolume"],
                y=group_sorted["OverlapPercent"],
                mode="lines",
                line=dict(dash="dot", color="gray", width=1),
                showlegend=False,
                hoverinfo="skip",
                opacity=0.8
            ))

    scatter_fig = px.scatter(
        group_df,
        x="ModelVolume",
        y="OverlapPercent",
        color="method_display",
        symbol="segment",
        symbol_map=group_symbols,
        category_orders={"segment": seg_list},
        labels={
            "ModelVolume": "Structure Volume (mL) for each Model",
            "OverlapPercent": "Consensus Volume (% of Structure Volume)",
            "method_display": "Segmentation Model"
        },
        hover_data=["caseID", "segment", "ModelVolume", "OverlapVolume"],
        custom_data=["url"],
        color_discrete_map=custom_palette
    )

    fig.add_traces(list(scatter_fig.data))

    fig.update_layout(
        legend_title="Method",
        legend=dict(x=1.05, y=1),
        width=1600,
        height=890,
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    fig.update_xaxes(title="Structure Volume (mL) for each Model", showgrid=True, gridcolor='lightgray', zeroline=False)
    fig.update_yaxes(title="Consensus Volume (% of Structure Volume)", showgrid=True, gridcolor='lightgray', zeroline=False)

    output_path = os.path.join(output_dir, f"Overlap_percent_of_model_volumes_grouped_{group_name}.html")
    post_script = """
      var plotDiv = document.getElementsByClassName('plotly-graph-div')[0];
      if (plotDiv) {{
        plotDiv.on('plotly_click', function(data){{
          if(data.points && data.points[0] && data.points[0].customdata){{
            var url = data.points[0].customdata[0];
            window.open(url, '_blank');
          }}
        }});
      }}
      var explanationDiv = document.createElement('div');
      plotDiv.parentNode.insertBefore(explanationDiv, plotDiv.nextSibling);
    """

    fig.write_html(
        output_path,
        include_plotlyjs=True,
        full_html=True,
        post_script=post_script
    )
    print(f"Interactive Plot for group '{group_name}' saved: {output_path}")
