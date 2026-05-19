"""
자동차 등록 통계 대시보드 — 모듈 버전
원본: app3.py  /  render(model_choice) 로 래핑하여 Appmain.py 에서 호출
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from modules.connect_db import load_data

COLUMN_LABELS = {
    "year_months": "원본 기준년월",
    "year_months_fmt": "기준년월",
    "stat_year": "연도",
    "model_year": "연식",
    "car_type": "차종",
    "usage_type": "이용목적",
    "region": "지역",
    "displacement": "배기량",
    "fuel_type": "연료",
    "gender": "성별",
    "age_group": "연령대",
    "legend_name": "범례",
    "registered_count": "등록 대수",
    "cnt_official": "관용",
    "cnt_private": "자가용",
    "cnt_business": "사업용",
    "cnt_total": "전체 합계",
    "cnt_gap": "증감 대수",
}

def make_unique_columns(columns):
    counts = {}
    unique = []
    for col in columns:
        if col not in counts:
            counts[col] = 0
            unique.append(col)
        else:
            counts[col] += 1
            unique.append(f"{col}_{counts[col] + 1}")
    return unique

def prepare_display_df(df):
    display_df = df.copy().replace("None", pd.NA)
    display_df = display_df.drop(
        columns=[c for c in ["id", "created_at", "updated_at"] if c in display_df.columns],
        errors="ignore",
    )
    display_df = display_df.rename(columns=COLUMN_LABELS)
    display_df.columns = make_unique_columns(display_df.columns)
    return display_df.fillna("-")

def style_chart(fig):
    fig.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#17324d"),
        title_font=dict(color="#0f2f55", size=17),
        legend_title_text="",
        margin=dict(l=20, r=20, t=60, b=20),
        yaxis=dict(tickformat=',d'),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#edf5fc", linecolor="#cfe4f7", type="category")
    fig.update_yaxes(showgrid=True, gridcolor="#edf5fc", linecolor="#cfe4f7")
    return fig

def render_view(view_mode, fig, df_display, chart_key=None):
    if not view_mode:
        st.info("자료 출력 방식을 선택해 주세요.")
        return

    if view_mode in ["그래프", "그래프 + 테이블(표)"]:
        if fig is None:
            st.info("선택한 조건에 맞는 그래프 데이터가 없습니다.")
        else:
            with st.container(key=chart_key):
                st.plotly_chart(style_chart(fig), use_container_width=True)

    if view_mode in ["테이블(표)", "그래프 + 테이블(표)"]:
        if view_mode == "그래프 + 테이블(표)":
            st.markdown("---")
            st.markdown("### 상세 데이터 테이블")
        st.caption("💡 컬럼명을 클릭하면 오름차순·내림차순으로 정렬할 수 있습니다.")
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ============================================================
# UI 테마 CSS 주입 (남색 테마 통일 및 미니멀 버튼 디자인)
# ============================================================
def inject_custom_css():
    st.markdown("""
    <style>
    /* Streamlit 기본 붉은색 테마를 남색으로 강제 덮어쓰기 */
    :root {
        --primary-color: #174f84 !important;
    }

    /* 슬라이더 컬러 및 글씨체 남색으로 통일 */
    div.stSlider > div[data-baseweb="slider"] > div > div > div {
        background-color: #174f84 !important;
    }
    div.stSlider > div[data-baseweb="slider"] > div > div > div[role="slider"] {
        background-color: #174f84 !important;
        border-color: #174f84 !important;
    }
    div.stSlider, div.stSlider label { font-family: inherit !important; }

    /* Segmented Control & Pills 선택 색상 남색 통일 */
    div[data-testid="stSegmentedControl"] label[data-checked="true"] > div,
    div[data-testid="stPills"] label[data-checked="true"] > div {
        background-color: #174f84 !important;
        color: white !important;
        border-color: #174f84 !important;
    }

    /* [새로운 디자인] 미니멀 플랫 버튼 (전체선택/초기화 용도) */
    div[data-testid="stButton"] button {
        background-color: transparent !important;
        color: #52677a !important; /* 눈에 덜 띄는 차분한 색상 */
        border: 1px solid #cfe4f7 !important;
        border-radius: 4px !important;
        padding: 0.1rem 0.3rem !important;
        min-height: 1.8rem !important; /* 버튼 높이 최소화 */
        font-size: 0.8rem !important; /* 글씨 크기 축소 */
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #f0f7ff !important;
        color: #174f84 !important;
        border-color: #174f84 !important;
    }
    div[data-testid="stButton"] button:active {
        background-color: #174f84 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# 모델 함수들
# ============================================================

def model_1_age_stats():
    st.markdown("<h2 style='font-size: 1.85rem; color: #0f2f55; margin-bottom: 0.8rem;'>연식 차량 대수 조회</h2>", unsafe_allow_html=True)
    st.markdown("---")

    df = load_data("SELECT * FROM car_age_stats WHERE year_months = '202604'")
    if df.empty: return

    usage_column = 'usage_type' if 'usage_type' in df.columns else 'usage'
    raw_usages = df[usage_column].unique()
    usage_display_map = {u: ('영업용+자가용+관용(합계)' if u in ['계', '합계', '전체'] else u) for u in raw_usages}
    desired_usage_order = ['영업용+자가용+관용(합계)', '자가용', '영업용', '관용']
    usage_options = [d for d in desired_usage_order if d in usage_display_map.values()]

    raw_cars = df['car_type'].unique()
    car_display_map = {c: ('합계' if c in ['계', '합계', '전체'] else c) for c in raw_cars}
    desired_car_order = ['합계', '승용', '승합', '화물', '특수']
    car_options = [d for d in desired_car_order if d in car_display_map.values()]

    raw_years = sorted(df['model_year'].unique(), reverse=True)
    year_options = [f"{y}년식" for y in raw_years]
    default_year = [f"2026년식"] if f"2026년식" in year_options else ([year_options[0]] if year_options else [])

    if "m1_years" not in st.session_state: st.session_state.m1_years = default_year
    if "m1_cars" not in st.session_state: st.session_state.m1_cars = []
    if "m1_usages" not in st.session_state: st.session_state.m1_usages = []

    col1, col2 = st.columns(2)
    with col1:
        st.pills("분석할 차종 선택", options=car_options, selection_mode="multi", key="m1_cars")
        st.pills("차량 용도별 구분 선택", options=usage_options, selection_mode="multi", key="m1_usages")
        
    with col2:
        # [새로운 레이아웃] 제목 라벨과 미니멀 버튼을 가로로 정렬
        hc1, hc2, hc3 = st.columns([5, 2.5, 2.5])
        with hc1:
            st.markdown("<div style='font-size:0.9rem; font-weight:600; padding-top:6px; color:#17324d;'>조회할 차량 연식 선택</div>", unsafe_allow_html=True)
        with hc2:
            if st.button("전체 선택", key="btn_m1_y_all", use_container_width=True): st.session_state.m1_years = year_options
        with hc3:
            if st.button("초기화", key="btn_m1_y_none", use_container_width=True): st.session_state.m1_years = []
                
        st.pills("연식 선택 (숨김 라벨)", options=year_options, selection_mode="multi", key="m1_years", label_visibility="collapsed")
        
        view_mode = st.segmented_control(
            "자료 출력 방식 선택",
            options=["그래프", "테이블(표)", "그래프 + 테이블(표)"],
            default="그래프 + 테이블(표)",
            key="m1_view_mode",
        )

    selected_cars_raw = [k for k, v in car_display_map.items() if v in st.session_state.m1_cars]
    selected_usages_raw = [k for k, v in usage_display_map.items() if v in st.session_state.m1_usages]
    year_map_back = {f"{y}년식": y for y in raw_years}
    selected_years_raw = [year_map_back[y] for y in st.session_state.m1_years]

    filtered_df = df[
        (df['model_year'].isin(selected_years_raw)) &
        (df['car_type'].isin(selected_cars_raw))
    ].copy()

    if selected_usages_raw:
        filtered_df = filtered_df[filtered_df[usage_column].isin(selected_usages_raw)]
    else:
        filtered_df = pd.DataFrame(columns=df.columns)

    if filtered_df.empty:
        st.info("조건(차종/차량 용도/차량 연식)을 올바르게 선택하시면 데이터가 표시됩니다.")
        return

    chart_df = filtered_df.copy()
    chart_df['model_year_disp'] = chart_df['model_year'].astype(str) + "년식"
    chart_df['car_type_disp'] = chart_df['car_type'].replace(['계', '합계'], '합계')
    
    usage_disp_mapped = chart_df[usage_column].map(lambda x: usage_display_map.get(x, x))
    chart_df['legend_name'] = chart_df['car_type_disp'] + " (" + usage_disp_mapped + ")"

    fig = None
    if view_mode in ["그래프", "그래프 + 테이블(표)"]:
        st.markdown("### 등록 대수 시각화")
        sort_option = st.segmented_control(
            "그래프 정렬 기준 선택",
            options=["연식 오름차순", "연식 내림차순", "등록대수 높은 순", "등록대수 낮은 순"],
            default="연식 오름차순",
            key="m1_sort_option_live",
        )
        if not sort_option: sort_option = "연식 오름차순"
        
        if sort_option == "연식 오름차순": chart_df = chart_df.sort_values(by='model_year', ascending=True)
        elif sort_option == "연식 내림차순": chart_df = chart_df.sort_values(by='model_year', ascending=False)
        elif sort_option == "등록대수 높은 순": chart_df = chart_df.sort_values(by='registered_count', ascending=False)
        elif sort_option == "등록대수 낮은 순": chart_df = chart_df.sort_values(by='registered_count', ascending=True)

        fig = px.bar(chart_df, x='model_year_disp', y='registered_count', color='legend_name', barmode='group',
                     title="연식별 차량 등록 대수 (2026년 04월 기준)",
                     labels={'model_year_disp': '차량연식', 'registered_count': '등록대수', 'legend_name': '차종(용도)'})

    df_display = filtered_df.copy()
    df_display['year_months_fmt'] = df_display['year_months'].astype(str).apply(lambda x: f"{x[:4]}-{x[4:6]}")
    df_display['model_year_disp'] = df_display['model_year'].astype(str) + "년식"
    df_display = df_display.rename(columns={
        'year_months_fmt': '기준년월', 'model_year_disp': '차량연식', 'car_type': '차종',
        usage_column: '이용목적', 'registered_count': '등록대수',
    })
    df_display['이용목적'] = df_display['이용목적'].replace(['계', '합계', '전체'], '영업용+자가용+관용(합계)')
    df_display['차종'] = df_display['차종'].replace(['계', '합계', '전체'], '합계')
    df_display = df_display[['기준년월', '차량연식', '차종', '이용목적', '등록대수']]

    render_view(view_mode, fig, df_display)


def model_2_region_analysis():
    st.markdown("<h2 style='font-size: 1.85rem; color: #0f2f55; margin-bottom: 0.8rem;'>연료/배기량별 차량등록 수</h2>", unsafe_allow_html=True)

    col_control1, col_control2 = st.columns(2)
    with col_control1:
        analysis_type = st.segmented_control(
            "분석 기준 선택", options=["연료별 조회", "배기량별 조회"], default="연료별 조회", key="m2_analysis_type",
        )
    with col_control2:
        view_mode = st.segmented_control(
            "자료 출력 방식 선택", options=["그래프", "테이블(표)", "그래프 + 테이블(표)"], default="그래프 + 테이블(표)", key="m2_view_mode",
        )
    st.markdown("---")

    if not analysis_type:
        st.info("분석 기준(연료별 혹은 배기량별)을 선택해 주세요.")
        return

    fig = None
    if analysis_type == "연료별 조회":
        df = load_data("SELECT * FROM car_fuel_stats")
        if df.empty: return

        months = sorted(df['year_months_fmt'].unique())
        start_month, end_month = st.select_slider(
            "조회할 시계열 기간(연료) 선택", options=months, value=(months[0], months[-1]), key="m2_fuel_slider"
        )

        CUSTOM_FUEL_ORDER = ["휘발유", "경유", "LPG", "하이브리드", "전기", "수소", "기타 연료"]
        existing_fuels = [f for f in CUSTOM_FUEL_ORDER if f in df['fuel_type'].unique()]
        remaining_fuels = [f for f in df['fuel_type'].unique() if f not in CUSTOM_FUEL_ORDER]
        fuel_options = existing_fuels + remaining_fuels

        if "m2_fuels" not in st.session_state: st.session_state.m2_fuels = []

        col1, col2 = st.columns(2)
        with col1:
            car_types = st.pills("분석할 차종 선택", options=sorted(df['car_type'].unique()), default=[], selection_mode="multi")
            usage_column = 'usage_type' if 'usage_type' in df.columns else 'usage'
            raw_usages = sorted(df[usage_column].unique())
            display_usages = ['사업자용 + 비사업자용(합계)' if u == '계' else u for u in raw_usages]
            selected_usage_display = st.pills("차량 용도별 선택", options=display_usages, default=None, selection_mode="single")
            usage_map = {('사업자용 + 비사업자용(합계)' if u == '계' else u): u for u in raw_usages}
            selected_usage_raw = usage_map.get(selected_usage_display) if selected_usage_display else None
        
        with col2:
            # [새로운 레이아웃]
            hc1, hc2, hc3 = st.columns([5, 2.5, 2.5])
            with hc1:
                st.markdown("<div style='font-size:0.9rem; font-weight:600; padding-top:6px; color:#17324d;'>분석할 연료 선택</div>", unsafe_allow_html=True)
            with hc2:
                if st.button("전체 선택", key="btn_m2_f_all", use_container_width=True): st.session_state.m2_fuels = fuel_options
            with hc3:
                if st.button("초기화", key="btn_m2_f_none", use_container_width=True): st.session_state.m2_fuels = []
                    
            st.pills("연료 선택 (숨김)", options=fuel_options, selection_mode="multi", key="m2_fuels", label_visibility="collapsed")

        filtered_df = df[
            (df['year_months_fmt'].between(start_month, end_month)) &
            (df['car_type'].isin(car_types)) &
            (df['fuel_type'].isin(st.session_state.m2_fuels))
        ].copy()

        if selected_usage_raw: filtered_df = filtered_df[filtered_df[usage_column] == selected_usage_raw]
        else: filtered_df = pd.DataFrame(columns=df.columns)

        if not filtered_df.empty: filtered_df['legend_name'] = filtered_df['car_type'] + " (" + filtered_df['fuel_type'] + ")"
        
        df_display = filtered_df.copy()
        if not df_display.empty:
            df_display = df_display.rename(columns={
                'year_months_fmt': '기준년월', 'fuel_type': '연료', 'car_type': '차종',
                usage_column: '이용목적', 'registered_count': '등록대수',
            })
            df_display['이용목적'] = df_display['이용목적'].replace('계', '사업자용 + 비사업자용(합계)')
            df_display = df_display[['기준년월', '연료', '차종', '이용목적', '등록대수']]

        if not filtered_df.empty:
            fig = px.line(filtered_df, x='year_months_fmt', y='registered_count', color='legend_name', markers=True,
                          title=f"연료 및 차종별 등록 대수 추이 ({start_month} ~ {end_month})",
                          labels={'year_months_fmt': '기준년월', 'registered_count': '등록대수', 'legend_name': '차종(연료)'})

    else:
        df = load_data("SELECT * FROM car_displacement_stats")
        if df.empty: return

        months = sorted(df['year_months_fmt'].unique())
        start_month, end_month = st.select_slider(
            "조회할 시계열 기간(배기량) 선택", options=months, value=(months[0], months[-1]), key="m2_disp_slider"
        )

        CUSTOM_DISP_ORDER = ["1000 미만", "1000 이상", "1600 이상", "2000 이상", "2500 이상", "저속전기차", "전기차"]
        existing_disps = [d for d in CUSTOM_DISP_ORDER if d in df['displacement'].unique()]
        disp_options = existing_disps + [d for d in df['displacement'].unique() if d not in CUSTOM_DISP_ORDER]

        col1, col2 = st.columns(2)
        with col1:
            regions = st.pills("분석할 지역 선택", options=sorted(df['region'].unique()), default=[], selection_mode="multi")
        with col2:
            displacements = st.pills("분석할 배기량 선택", options=disp_options, default=[], selection_mode="multi")

        filtered_df = df[
            (df['year_months_fmt'].between(start_month, end_month)) &
            (df['region'].isin(regions)) &
            (df['displacement'].isin(displacements))
        ].copy()

        if not filtered_df.empty: filtered_df['legend_name'] = filtered_df['region'] + " - " + filtered_df['displacement']
        
        df_display = filtered_df.copy()
        if not df_display.empty:
            df_display = df_display.rename(columns={
                'year_months_fmt': '기준년월', 'region': '지역', 'displacement': '배기량', 'registered_count': '등록대수',
            })
            df_display = df_display[['기준년월', '지역', '배기량', '등록대수']]

        if not filtered_df.empty:
            fig = px.line(filtered_df, x='year_months_fmt', y='registered_count', color='legend_name', markers=True,
                          title=f"지역 및 배기량별 등록 대수 추이 ({start_month} ~ {end_month})",
                          labels={'year_months_fmt': '기준년월', 'registered_count': '등록대수', 'legend_name': '지역-배기량'})

    if filtered_df.empty:
        st.info("조건(차종/연료/차량 용도 또는 지역/배기량)을 올바르게 선택하시면 데이터가 표시됩니다.")
        return

    render_view(view_mode, fig, df_display)


def model_3_gender_age_stats():
    st.markdown("<h2 style='font-size: 1.85rem; color: #0f2f55; margin-bottom: 0.8rem;'>성별·연령별 등록 추이</h2>", unsafe_allow_html=True)
    df = load_data("SELECT * FROM car_gender_age_stats")
    if df.empty: return

    df = df[
        (df['region'] == '합계') &
        (~df['gender'].isin(['계', '기타'])) &
        (df['age_group'] != '계')
    ].copy()

    months = sorted(df['year_months_fmt'].unique())
    start_month, end_month = st.select_slider("조회할 기간 선택", options=months, value=(months[0], months[-1]))

    df['legend_name'] = df['gender'] + " " + df['age_group']
    age_options = sorted(df['age_group'].unique())

    if "m3_ages" not in st.session_state: st.session_state.m3_ages = []

    col1, col2 = st.columns(2)
    with col1:
        genders = st.pills("성별 선택", options=sorted(df['gender'].unique()), default=[], selection_mode="multi")
    with col2:
        # [새로운 레이아웃]
        hc1, hc2, hc3 = st.columns([5, 2.5, 2.5])
        with hc1:
            st.markdown("<div style='font-size:0.9rem; font-weight:600; padding-top:6px; color:#17324d;'>연령대 선택</div>", unsafe_allow_html=True)
        with hc2:
            if st.button("전체 선택", key="btn_m3_a_all", use_container_width=True): st.session_state.m3_ages = age_options
        with hc3:
            if st.button("초기화", key="btn_m3_a_none", use_container_width=True): st.session_state.m3_ages = []
                
        st.pills("연령대 선택 (숨김)", options=age_options, selection_mode="multi", key="m3_ages", label_visibility="collapsed")

    filtered_df = df[
        (df['year_months_fmt'].between(start_month, end_month)) &
        (df['gender'].isin(genders)) &
        (df['age_group'].isin(st.session_state.m3_ages))
    ]

    st.markdown("---")
    view_mode = st.segmented_control("자료 출력 방식 선택", options=["그래프", "테이블(표)"], default="그래프")

    if filtered_df.empty:
        st.info("성별과 연령대를 선택하시면 데이터가 표시됩니다.")
        return

    fig = px.line(
        filtered_df, x='year_months_fmt', y='registered_count', color='legend_name', markers=True,
        title=f"성별 및 연령별 등록 대수 추이 ({start_month} ~ {end_month})",
        labels={'year_months_fmt': '기준년월', 'registered_count': '등록 대수', 'legend_name': '성별·연령대'},
    )

    display_df = (
        prepare_display_df(filtered_df)
        .drop(columns=["지역", "기준년월", "성별·연령대"], errors="ignore")
        .rename(columns={"원본 기준년월": "기준년월"})
    )
    
    render_view(view_mode, fig, display_df, chart_key="gender_age_chart_card")


def model_4_yearly_stats():
    st.markdown("<h2 style='font-size: 1.85rem; color: #0f2f55; margin-bottom: 0.8rem;'>연간 자동차 등록 추이</h2>", unsafe_allow_html=True)
    df = load_data("SELECT * FROM car_yearly_stats")
    if df.empty: return

    df = df[
        (~df['car_type'].isin(['합계', '계'])) &
        (~df['usage_type'].isin(['합계', '계']))
    ].copy()

    year_column = 'year' if 'year' in df.columns else 'model_year' if 'model_year' in df.columns else 'stat_year'
    df['year_disp'] = df[year_column].astype(float).astype(int).astype(str) + "년"

    years_options = sorted(df['year_disp'].unique())
    start_year, end_year = st.select_slider("조회할 기간 선택", options=years_options, value=(years_options[0], years_options[-1]))

    col1, col2 = st.columns(2)
    with col1:
        car_types = st.pills("차종 선택", options=sorted(df['car_type'].unique()), default=[], selection_mode="multi")
    with col2:
        usage_types = st.pills("이용목적 선택", options=sorted(df['usage_type'].unique()), default=[], selection_mode="multi")

    filtered_df = df[
        (df['year_disp'] >= start_year) & (df['year_disp'] <= end_year) &
        (df['car_type'].isin(car_types)) &
        (df['usage_type'].isin(usage_types))
    ]

    st.markdown("---")
    view_mode = st.segmented_control("자료 출력 방식 선택", options=["그래프", "테이블(표)"], default="그래프")

    if filtered_df.empty:
        st.info("차종과 이용목적을 선택하시면 데이터가 표시됩니다.")
        return

    fig = px.bar(
        filtered_df, x='year_disp', y='registered_count', color='car_type', barmode='group',
        title=f"연간 자동차 등록 대수 추이 ({start_year} ~ {end_year})",
        labels={'year_disp': '연도', 'registered_count': '등록 대수', 'car_type': '차종'},
    )

    display_df = prepare_display_df(filtered_df)
    if '연도' in display_df.columns: display_df = display_df.drop(columns=['연도'])
    if 'year_disp' in display_df.columns: display_df = display_df.rename(columns={'year_disp': '연도'})
    table_column_order = ["연도", "차종", "이용목적", "등록 대수"]
    display_df = display_df[[col for col in table_column_order if col in display_df.columns]]

    render_view(view_mode, fig, display_df, chart_key="yearly_chart_card")


def model_5_region_ranking():
    st.markdown("<h2 style='font-size: 1.85rem; color: #0f2f55; margin-bottom: 0.8rem;'>지역별 등록 증감 순위</h2>", unsafe_allow_html=True)
    df = load_data("SELECT * FROM car_region_stats")
    if df.empty: return

    df = df[
        (~df['car_type'].isin(['합계', '계'])) &
        (df['region'] != '합계')
    ].copy()

    target_columns = {
        'cnt_official': '관용', 'cnt_private': '자가용', 'cnt_business': '사업용', 'cnt_total': '전체 합계',
    }

    col1, col2 = st.columns(2)
    with col1:
        car_type = st.pills("차종 선택", options=sorted(df['car_type'].unique()), default=None, selection_mode="single")
    with col2:
        target_kor = st.pills("조회 기준 선택", options=list(target_columns.values()), default="전체 합계", selection_mode="single")

    months = sorted(df['year_months_fmt'].unique())

    st.markdown("<h5 style='font-size: 1.1rem; color: #0f2f55;'>비교할 시점 선택</h5>", unsafe_allow_html=True)
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        past_month = st.selectbox("비교할 시점 선택 시점1 (과거)", months, index=0)
    with col_time2:
        recent_month = st.selectbox("비교할 시점 선택 시점2 (최신)", months, index=len(months) - 1)

    if not car_type or not target_kor:
        st.info("차종과 조회기준을 선택하면 지역별 등록 증감 순위를 확인할 수 있습니다.")
        return

    target_col = [k for k, v in target_columns.items() if v == target_kor][0]

    df_filtered = df[df['car_type'] == car_type]
    df_past = df_filtered[df_filtered['year_months_fmt'] == past_month][['region', target_col]]
    df_recent = df_filtered[df_filtered['year_months_fmt'] == recent_month][['region', target_col]]

    df_merge = pd.merge(df_past, df_recent, on='region', suffixes=('_past', '_recent'))
    df_merge['cnt_gap'] = df_merge[f'{target_col}_recent'] - df_merge[f'{target_col}_past']

    df_display = df_merge.rename(columns={
        'region': '지역',
        f'{target_col}_past': f'{past_month} 등록수',
        f'{target_col}_recent': f'{recent_month} 등록수',
        'cnt_gap': '증감 대수',
    })

    st.markdown("---")
    view_mode = st.segmented_control("자료 출력 방식 선택", options=["그래프", "테이블(표)"], default="그래프")
    
    fig = None
    if not df_merge.empty and view_mode in ["그래프", "그래프 + 테이블(표)"]:
        sort_col1, sort_col2 = st.columns(2)
        with sort_col1:
            sort_target = st.segmented_control("그래프 정렬 기준", options=[f"최신값 {target_kor} 기준", "증감량 기준"], default=f"최신값 {target_kor} 기준")
        with sort_col2:
            sort_order = st.segmented_control("정렬 방향", options=["내림차순", "오름차순"], default="내림차순")
        ascending = sort_order == "오름차순"

        if sort_target == "증감량 기준":
            chart_df = df_merge.sort_values(by='cnt_gap', ascending=ascending)
            y_axis = 'cnt_gap'
            title_text = f"지역별 자동차 등록 증감량 순위 ({past_month} vs {recent_month})"
        else:
            chart_df = df_merge.sort_values(by=f'{target_col}_recent', ascending=ascending)
            y_axis = f'{target_col}_recent'
            title_text = f"지역별 자동차 등록 최신 순위 ({recent_month} 기준)"

        fig = px.bar(
            chart_df, x='region', y=y_axis, title=title_text,
            labels={'region': '지역', y_axis: target_kor if y_axis != 'cnt_gap' else '증감 대수'},
        )

    table_column_order = ["지역", f"{past_month} 등록수", f"{recent_month} 등록수", "증감 대수"]
    display_df = df_display[[col for col in table_column_order if col in df_display.columns]].copy()

    render_view(view_mode, fig, display_df, chart_key="region_rank_chart_card")


# ============================================================
# 디스패처
# ============================================================
MODELS = [
    "연식 차량 대수 조회",
    "연료/배기량별 차량등록 수",
    "성별·연령별 등록 추이",
    "연간 자동차 등록 추이",
    "지역별 등록 증감 순위",
]

_MODEL_FN = {
    "연식 차량 대수 조회":      model_1_age_stats,
    "연료/배기량별 차량등록 수": model_2_region_analysis,
    "성별·연령별 등록 추이":     model_3_gender_age_stats,
    "연간 자동차 등록 추이":     model_4_yearly_stats,
    "지역별 등록 증감 순위":     model_5_region_ranking,
    "1. 연식 차량 대수 조회":      model_1_age_stats,
    "2. 연료/배기량별 차량등록 수": model_2_region_analysis,
    "3. 성별·연령별 등록 추이":     model_3_gender_age_stats,
    "4. 연간 자동차 등록 추이":     model_4_yearly_stats,
    "5. 지역별 등록 증감 순위":     model_5_region_ranking,
}

def render(model_choice: str):
    # CSS 먼저 주입하여 전체 테마 색상(남색) 통일
    inject_custom_css()
    
    st.title("📊 자동차 등록 통계 대시보드")
    st.markdown(
        '<p style="color:#315a7c; font-size:1.02rem; margin-top:-0.35rem; margin-bottom:1.25rem;">'
        '자동차 등록 데이터를 조건별로 조회하고 그래프와 표로 비교합니다.'
        '</p>',
        unsafe_allow_html=True,
    )
    fn = _MODEL_FN.get(model_choice)
    if fn:
        fn()
    else:
        st.error(f"알 수 없는 모델: {model_choice}")