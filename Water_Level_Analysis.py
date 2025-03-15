import streamlit as st
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from datetime import datetime

# App Configuration
st.set_page_config(
    page_title="Aquifer Analysis Suite",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #f0f2f6;}
    .stDownloadButton button {background-color: #4CAF50!important;}
    div[data-baseweb="select"] {border-radius: 8px!important;}
    .header-text {color: #1a73e8; font-family: 'Arial';}
    .metric-box {padding: 15px; background: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
</style>
""", unsafe_allow_html=True)

def main():
    # App Header
    st.title("📊 Aquifer Performance Analyzer")
    st.markdown("""
    **Analyze well pumping cycles and aquifer characteristics**  
    Upload water level data to calculate key hydrogeological parameters.
    """)
    
    # File Upload Section
    uploaded_file = st.file_uploader("Upload Water Level Data (CSV format)", type=["csv"])
    
    if uploaded_file:
        try:
            with st.spinner('🔍 Analyzing data... This may take a moment'):
                # Data Processing (Original Code Core)
                df = pd.read_csv(uploaded_file, sep=';', parse_dates=['Timestamp'])
                df = df.sort_values('Timestamp').reset_index(drop=True)
                levels = df['Level above Pump'].values
                
                # Peak Detection
                peaks, _ = find_peaks(levels, prominence=0)
                df['is_peak'] = False
                df.loc[peaks, 'is_peak'] = True

                cycles = []
                cumulative_drawdown = 0

                # Cycle Processing
                for i in range(len(peaks) - 1):
                    start_idx = peaks[i]
                    end_idx = peaks[i + 1]
                    cycle_data = df.iloc[start_idx:end_idx + 1]

                    if len(cycle_data) < 2:
                        continue

                    swl = cycle_data.iloc[0]['Level above Pump']
                    min_level_idx = cycle_data['Level above Pump'].idxmin()
                    min_level = cycle_data.loc[min_level_idx, 'Level above Pump']
                    max_drawdown_value = swl - min_level

                    if max_drawdown_value < 2:
                        continue

                    # Timing Calculations
                    start_time = cycle_data.iloc[0]['Timestamp']
                    min_time = cycle_data.loc[min_level_idx, 'Timestamp']
                    end_time = cycle_data.iloc[-1]['Timestamp']

                    # Metric Calculations
                    time_to_max_drawdown = (min_time - start_time).total_seconds() / 3600
                    recovery_time = (end_time - min_time).total_seconds() / 3600
                    drawdown_rate = max_drawdown_value / time_to_max_drawdown if time_to_max_drawdown > 0 else 0
                    recharge_rate = max_drawdown_value / recovery_time if recovery_time > 0 else 0
                    recovery_level = 0.9 * swl
                    recovery_subset = cycle_data[cycle_data['Level above Pump'] >= recovery_level]
                    
                    # 90% Recovery Time Calculation
                    time_to_90_recovery = -1* (recovery_subset['Timestamp'].iloc[0] - min_time).total_seconds() / 3600 \
                        if not recovery_subset.empty else np.nan

                    # Additional Metrics
                    cycle_duration = (end_time - start_time).total_seconds() / 3600
                    hourly_fluctuations = (swl - min_level) / cycle_duration if cycle_duration > 0 else 0
                    cumulative_drawdown += max_drawdown_value
                    recharge_volume = max_drawdown_value * 1  # Assuming unit area

                    # Store Cycle Data
                    cycles.append({
                        'cycle_number': len(cycles) + 1,
                        'start_time': start_time,
                        'SWL (m)': round(swl, 1),
                        'Max Drawdown (m)': round(max_drawdown_value, 1),
                        'Drawdown Rate (m/hr)': round(drawdown_rate, 1),
                        'Recovery Time (hr)': round(recovery_time, 2),
                        'Recharge Rate (m/hr)': round(recharge_rate, 1),
                        'Time to Max Drawdown (hr)': round(time_to_max_drawdown, 2),
                        '90% Recovery Time (hr)': round(time_to_90_recovery, 2) if not np.isnan(time_to_90_recovery) else np.nan,
                        'Hourly Fluctuation (m/hr)': round(hourly_fluctuations, 1),
                        'Cumulative Drawdown (m)': round(cumulative_drawdown, 1),
                        'Recharge Volume (m³)': round(recharge_volume, 1)
                    })

            # Results Display
            st.success("✅ Analysis completed successfully!")
            
            # Create DataFrames
            if cycles:
                df_cycles = pd.DataFrame(cycles)
                df_summary = create_summary(df_cycles)

                # Main Dashboard
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.subheader("📋 Cycle Summary")
                    st.dataframe(
                        df_cycles.style.format({
                            'SWL (m)': '{:.1f}',
                            'Max Drawdown (m)': '{:.1f}',
                            '90% Recovery Time (hr)': '{:.2f}'
                        }),
                        height=400,
                        use_container_width=True
                    )
                    
                    # Download Section
                    st.download_button(
                        label="📥 Download Cycle Data",
                        data=df_cycles.to_csv(index=False),
                        file_name=f'well_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )

                with col2:
                    st.subheader("📈 Key Metrics")
                    
                    # Top Metrics
                    metric_cols = st.columns(3)
                    with metric_cols[0]:
                        st.markdown(f"""
                        <div class="metric-box">
                            <h4>Total Cycles</h4>
                            <h2>{len(df_cycles)}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with metric_cols[1]:
                        st.markdown(f"""
                        <div class="metric-box">
                            <h4>Avg Drawdown</h4>
                            <h2>{df_cycles['Max Drawdown (m)'].mean():.1f} m</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with metric_cols[2]:
                        st.markdown(f"""
                        <div class="metric-box">
                            <h4>Max Recovery Time</h4>
                            <h2>{df_cycles['Recovery Time (hr)'].max():.1f} hr</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Summary Table
                    st.markdown("**Statistical Summary**")
                    st.dataframe(
                        df_summary.style.format({
                            'Min': '{:.2f}',
                            'Average': '{:.2f}',
                            'Max': '{:.2f}'
                        }),
                        use_container_width=True,
                        height=300
                    )

                # Visualizations
                st.subheader("📊 Data Visualization")
                tab1, tab2 = st.tabs(["Water Level Timeline", "Parameter Distribution"])
                
                with tab1:
                    st.line_chart(df.set_index('Timestamp')['Level above Pump'])
                    
                with tab2:
                    selected_param = st.selectbox("Select Parameter to Visualize", 
                                                options=['Max Drawdown (m)', 'Recovery Time (hr)', 
                                                        'Drawdown Rate (m/hr)', '90% Recovery Time (hr)'])
                    st.bar_chart(df_cycles[selected_param])

            else:
                st.warning("⚠️ No valid pumping cycles detected (drawdown <2m)")

        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.stop()

def create_summary(df):
    """Generate summary statistics DataFrame"""
    params = ['SWL (m)', 'Max Drawdown (m)', 'Drawdown Rate (m/hr)', 
             'Recovery Time (hr)', 'Recharge Rate (m/hr)', 'Time to Max Drawdown (hr)',
             '90% Recovery Time (hr)', 'Hourly Fluctuation (m/hr)', 
             'Cumulative Drawdown (m)', 'Recharge Volume (m³)']
    
    summary_data = []
    for param in params:
        summary_data.append({
            'Parameter': param,
            'Min': df[param].min(),
            'Average': df[param].mean(),
            'Max': df[param].max()
        })
    
    return pd.DataFrame(summary_data)

if __name__ == "__main__":
    main()
