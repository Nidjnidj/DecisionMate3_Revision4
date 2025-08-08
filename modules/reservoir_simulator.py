import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import time
import pandas as pd
import io
import zipfile

def run(T):
    st.title("🧪 Reservoir Flow Simulator (Black Oil – Pressure + Sw + Production)")
    st.markdown("Simulates pressure, water saturation, and production in a 2D reservoir.")

    # Step 1: Grid & Time Setup
    st.subheader("Step 1: Grid and Time Setup")
    nx = st.number_input("Number of Grid Blocks in X", min_value=1, value=5)
    ny = st.number_input("Number of Grid Blocks in Y", min_value=1, value=5)
    dx = st.number_input("Grid Block Size (ft)", min_value=10.0, value=100.0)
    dt = st.number_input("Time Step (days)", min_value=0.1, value=1.0)
    n_steps = st.number_input("Number of Time Steps", min_value=1, value=10)

    # Step 2: Reservoir Properties
    st.subheader("Step 2: Reservoir Properties")
    phi = st.number_input("Porosity (fraction)", min_value=0.01, max_value=1.0, value=0.2)
    perm = st.number_input("Permeability (mD)", min_value=0.01, value=100.0)
    mu = st.number_input("Viscosity (cp)", min_value=0.01, value=1.0)
    ct = st.number_input("Total Compressibility (1/psi)", min_value=1e-6, value=1e-5, format="%.6f")

    # Step 3: Initial and Boundary Conditions
    st.subheader("Step 3: Initial & Boundary Conditions")
    p_init = st.number_input("Initial Pressure (psi)", value=3000.0)
    p_boundary = st.number_input("Boundary Pressure (psi)", value=3000.0)
    p_prod = st.number_input("Producer Pressure (psi)", value=1000.0)
    st.markdown("### 👷‍♂️ Define Wells")

    n_inj = st.number_input("Number of Injectors", min_value=1, value=1)
    n_prod = st.number_input("Number of Producers", min_value=1, value=1)

    injectors = []
    producers = []

    for i in range(n_inj):
        col1, col2 = st.columns(2)
        with col1:
            x = st.number_input(f"Injector {i+1} X", 0, nx - 1, i)
        with col2:
            y = st.number_input(f"Injector {i+1} Y", 0, ny - 1, i)
        injectors.append((x, y))

    for i in range(n_prod):
        col1, col2 = st.columns(2)
        with col1:
            x = st.number_input(f"Producer {i+1} X", 0, nx - 1, nx // 2)
        with col2:
            y = st.number_input(f"Producer {i+1} Y", 0, ny - 1, ny // 2)
        producers.append((x, y))

    run_sim = st.button("Run Simulation")

    if run_sim:
        # Initialize
        P = np.full((nx, ny), p_init)
        Sw = np.zeros((nx, ny))

        for inj_x, inj_y in injectors:
            Sw[inj_x, inj_y] = 1.0




        D = (0.001127 * perm) / (phi * mu * ct)
        pressure_maps = []
        saturation_maps = []

        cum_water_injected = 0.0
        cum_fluids_produced = 0.0
        flow_factor = 0.001  # arbitrary scaling unit

        # Main simulation loop
        for step in range(n_steps):
            P_new = P.copy()
            Sw_new = Sw.copy()

            for i in range(1, nx - 1):
                for j in range(1, ny - 1):
                    # Pressure update
                    laplacian = (P[i+1,j] + P[i-1,j] + P[i,j+1] + P[i,j-1] - 4*P[i,j]) / (dx ** 2)
                    P_new[i,j] = P[i,j] + D * dt * laplacian

                    # Fractional flow (simple)
                    sw = Sw[i, j]
                    mu_w = 1.0
                    mu_o = 5.0
                    fw = (sw / mu_w) / (sw / mu_w + (1 - sw) / mu_o)

                    for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < nx and 0 <= nj < ny:
                            dP = P[ni, nj] - P[i, j]
                            if dP > 0:
                                Sw_new[i, j] += 0.01 * fw

                    Sw_new[i, j] = max(0.0, min(1.0, Sw_new[i, j]))

            # Apply boundary & well conditions
            P_new[0, :] = P_new[-1, :] = p_boundary
            P_new[:, 0] = P_new[:, -1] = p_boundary
        for prod_x, prod_y in producers:
            P_new[prod_x, prod_y] = p_prod
        for inj_x, inj_y in injectors:
            Sw_new[inj_x, inj_y] = 1.0


            # Track production & injection
            q_inj = 0.0
            for inj_x, inj_y in injectors:
                for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                    ni, nj = inj_x + di, inj_y + dj
                    if 0 <= ni < nx and 0 <= nj < ny:
                        dP = P[ni, nj] - P[inj_x, inj_y]
                        if dP > 0:
                            q_inj += flow_factor * dP
            cum_water_injected += q_inj * dt


            q_prod = 0.0
            for prod_x, prod_y in producers:
                for di, dj in [(-1,0), (1,0), (0,-1), (0,1)]:
                    ni, nj = prod_x + di, prod_y + dj
                    if 0 <= ni < nx and 0 <= nj < ny:
                        dP = P[prod_x, prod_y] - P[ni, nj]
                        if dP > 0:
                            q_prod += flow_factor * dP
            cum_fluids_produced += q_prod * dt

            # Save maps
            P = P_new
            Sw = Sw_new
            pressure_maps.append(P.copy())
            saturation_maps.append(Sw.copy())

        # Store for display
        st.session_state["pressure_maps"] = pressure_maps
        st.session_state["saturation_maps"] = saturation_maps
        st.session_state["n_steps"] = n_steps
        st.session_state["dt"] = dt
        st.session_state["cum_water_injected"] = cum_water_injected
        st.session_state["cum_fluids_produced"] = cum_fluids_produced

        st.success(f"✅ Simulation completed for {n_steps} steps.")

    # Display results
    if "pressure_maps" in st.session_state and st.session_state["pressure_maps"]:
        pressure_maps = st.session_state["pressure_maps"]
        saturation_maps = st.session_state["saturation_maps"]
        n_steps = len(pressure_maps)
        dt = st.session_state["dt"]
        cum_water_injected = st.session_state["cum_water_injected"]
        cum_fluids_produced = st.session_state["cum_fluids_produced"]

        if n_steps > 1:
            step_select = st.slider("Select Time Step", 1, n_steps, n_steps)
        else:
            step_select = 1


        st.subheader(f"📈 Pressure Distribution – Step {step_select}")
        fig, ax = plt.subplots()
        c = ax.imshow(pressure_maps[step_select - 1], cmap='coolwarm', origin='lower')


        for x, y in injectors:
            ax.plot(y, x, 'bo')  # blue for injector
        for x, y in producers:
            ax.plot(y, x, 'ro')  # red for producer

        ax.legend(loc="upper right")
        plt.colorbar(c, ax=ax, label='Pressure (psi)')
        st.pyplot(fig)



        st.subheader(f"💧 Water Saturation – Step {step_select}")

        fig2, ax2 = plt.subplots()
        s = ax2.imshow(saturation_maps[step_select - 1], cmap="Blues", origin="lower", vmin=0, vmax=1)
        for x, y in injectors:
            ax2.plot(y, x, 'bo')  # blue for injector
        for x, y in producers:
            ax2.plot(y, x, 'ro')  # red for producer

        ax2.legend(loc="upper right")
        plt.colorbar(s, ax=ax2, label="Water Saturation (Sw)")
        st.pyplot(fig2)


        for i, (px, py) in enumerate(producers):
            st.markdown(f"📍 Pressure at Producer {i+1} ({px},{py}): **{pressure_maps[step_select-1][px, py]:.2f} psi**")

        # ✅ Animate Pressure
        if st.checkbox("▶️ Animate Pressure"):
            st.subheader("🎞️ Pressure Animation")
            fig, ax = plt.subplots()
            plot = ax.imshow(pressure_maps[0], cmap="coolwarm", origin="lower")
            for x, y in injectors:
                ax.plot(y, x, 'bo', label="Injector")
            for x, y in producers:
                ax.plot(y, x, 'ro', label="Producer")

            ax.legend(loc="upper right")
            cbar = plt.colorbar(plot, ax=ax, label="Pressure (psi)")
            title = ax.set_title("")
            placeholder = st.empty()

            for step in range(n_steps):
                plot.set_data(pressure_maps[step])
                title.set_text(f"Step {step+1} - Day {dt*(step+1):.1f}")
                with placeholder:
                    st.pyplot(fig)
                time.sleep(0.4)

            st.success("🎬 Pressure animation completed")

        # ✅ Animate Saturation
        if st.checkbox("💧 Animate Saturation"):
            st.subheader("🎞️ Water Saturation Animation")
            fig, ax = plt.subplots()
            plot = ax.imshow(saturation_maps[0], cmap="Blues", origin="lower", vmin=0, vmax=1)
            for x, y in injectors:
                ax.plot(y, x, 'bo', label="Injector")
            for x, y in producers:
                ax.plot(y, x, 'ro', label="Producer")

            ax.legend(loc="upper right")
            cbar = plt.colorbar(plot, ax=ax, label="Sw")
            title = ax.set_title("")
            placeholder = st.empty()

            for step in range(n_steps):
                plot.set_data(saturation_maps[step])
                title.set_text(f"Step {step+1} - Day {dt*(step+1):.1f}")
                with placeholder:
                    st.pyplot(fig)
                time.sleep(0.4)

            st.success("💧 Saturation animation completed")

        # ✅ Production Summary
        st.subheader("📊 Production Summary")
        st.markdown(f"💧 **Cumulative Water Injected:** {cum_water_injected:.2f} units")
        st.markdown(f"🛢️ **Cumulative Fluids Produced:** {cum_fluids_produced:.2f} units")

        # 🔽 BEGIN EXPORT BLOCK
        st.subheader("📤 Export Simulation Results")

        step_data = step_select - 1  # Python index

        # Convert pressure & saturation maps for selected step to DataFrame
        df_pressure = pd.DataFrame(pressure_maps[step_data])
        df_saturation = pd.DataFrame(saturation_maps[step_data])

        # Button to download pressure CSV
        csv_pressure = df_pressure.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Pressure Map (CSV)",
            data=csv_pressure,
            file_name=f"pressure_step_{step_select}.csv",
            mime='text/csv'
        )

        # Button to download saturation CSV
        csv_saturation = df_saturation.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Saturation Map (CSV)",
            data=csv_saturation,
            file_name=f"saturation_step_{step_select}.csv",
            mime='text/csv'
        )

        # Production summary as CSV
        prod_summary = pd.DataFrame({
            "Metric": ["Water Injected", "Fluids Produced"],
            "Value": [cum_water_injected, cum_fluids_produced]
        })
        csv_summary = prod_summary.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Production Summary (CSV)",
            data=csv_summary,
            file_name="production_summary.csv",
            mime='text/csv'
        )

        # Optional: Export everything as ZIP
        if st.checkbox("🗜️ Export All as ZIP"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                zf.writestr(f"pressure_step_{step_select}.csv", csv_pressure.decode("utf-8"))
                zf.writestr(f"saturation_step_{step_select}.csv", csv_saturation.decode("utf-8"))
                zf.writestr("production_summary.csv", csv_summary.decode("utf-8"))
            st.download_button(
                label="⬇️ Download All Results (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="simulation_results.zip",
                mime="application/zip"
            )
        # 🔼 END EXPORT BLOCK
