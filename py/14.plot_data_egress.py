import matplotlib.pyplot as plt
import numpy as np

plt.style.use('dark_background')

# AWS & OCI Cost Calculations
def aws_cost(x):
    cost = np.zeros_like(x, dtype=float)
    mask1 = (x > 100) & (x <= 10000)
    cost[mask1] = (x[mask1] - 100) * 0.09
    mask2 = (x > 10000) & (x <= 50000)
    cost[mask2] = 891 + (x[mask2] - 10000) * 0.085
    mask3 = (x > 50000) & (x <= 150000)
    cost[mask3] = 4291 + (x[mask3] - 50000) * 0.07
    mask4 = x > 150000
    cost[mask4] = 11291 + (x[mask4] - 150000) * 0.05
    return cost

def oci_cost(x, rate_per_tb):
    cost = np.zeros_like(x, dtype=float)
    mask = x > 10000
    cost[mask] = ((x[mask] - 10000) / 1000.0) * rate_per_tb
    return cost

x = np.geomspace(10, 500000, 1000)
y_aws = aws_cost(x)
y_oci_na_eu = oci_cost(x, 8.50)
y_oci_apac_sa = oci_cost(x, 25.00)
y_oci_mea = oci_cost(x, 50.00)

val_100tb = 100000
c_aws_100tb = float(aws_cost(np.array([val_100tb]))[0])
c_oci_na_100tb = float(oci_cost(np.array([val_100tb]), 8.50)[0])
diff_100tb = c_aws_100tb - c_oci_na_100tb
pct_saving = (diff_100tb / c_aws_100tb) * 100

x_ticks = [100, 1000, 10000, 100000, 500000]
x_labels = ['100 GB\n(AWS Free Tier*)', '1 TB', '10 TB\n(OCI Free Tier)', '100 TB', '500 TB']

fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
fig.patch.set_facecolor('#0b132b')
ax.set_facecolor('#0b132b')

aws_color_lighter = '#ff9800'  
oci_red_darker = '#c53030'     
emerald_green = '#10b981'

# Tracciamento linee
ax.plot(x, y_aws, color=aws_color_lighter, linewidth=3.5, linestyle='-', label=r"AWS: All Regions", zorder=5)
ax.plot(x, y_oci_na_eu, color=oci_red_darker, linewidth=3, linestyle='-', label=r"OCI: EU, North America & UK", zorder=4)

ax.plot(x, y_oci_apac_sa, color=oci_red_darker, linewidth=2.5, linestyle='-', marker='d', markevery=40, markersize=5.5, label=r"OCI: APAC & South America", zorder=4)

ax.plot(x, y_oci_mea, color=oci_red_darker, linewidth=2, linestyle='--', label=r"OCI: Middle East & Africa", zorder=4)

ax.axvline(x=100000, color='#ffffff', linestyle='--', linewidth=1.2, alpha=0.8, zorder=6)

ax.scatter(100000, c_aws_100tb, color=aws_color_lighter, s=90, zorder=7, edgecolors='white', linewidth=2)
ax.scatter(100000, c_oci_na_100tb, color=oci_red_darker, s=90, zorder=7, edgecolors='white', linewidth=2)

ax.set_xscale('log')

ax.set_xticks(x_ticks)
ax.set_xticklabels(x_labels, color='#94a3b8', fontsize=12, fontweight='medium')

ax.grid(True, which="both", ls="-", color="#1c2541", alpha=0.8, linewidth=0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#3a506b')
ax.spines['bottom'].set_color('#3a506b')
ax.tick_params(colors='#94a3b8', labelsize=12)

ax.set_title('Monthly Data Egress\nCost Breakdown', fontsize=22, fontweight='bold', color='#ffffff', pad=22)
ax.set_xlabel('Volume Dati Mensile (GB / TB - Scala Logaritmica)', fontsize=14, fontweight='semibold', color='#cbd5e1', labelpad=12)
ax.set_ylabel('Costo Totale Mensile ($)', fontsize=14, fontweight='semibold', color='#cbd5e1', labelpad=12)

# --- MODIFICA POSIZIONE BOX ---
box_x = 0.50  
box_y = 0.45  

bbox_props = dict(boxstyle="round,pad=0.85", facecolor="#ffffff", edgecolor=emerald_green, alpha=0.98, lw=3.5)

box_text = (
    r"CONFRONTO A 100 TB / MESE" + "\n"
    "──────────────────────\n"
    r"AWS Cost: $\bf{\$7,791.00}$" + "\n"
    r"OCI Cost (EU): $\bf{\$765.00}$" + "\n"
    "──────────────────────\n"
    r"Differenziale: $\bf{\$7,026.00}$ / mese" + "\n"
    r"Taglio Costi: $\bf{-90.2\%}$ con OCI"
)

ax.text(box_x, box_y, box_text, transform=ax.transAxes,
        fontsize=13.5, color='#0f172a',
        fontfamily='sans-serif',
        verticalalignment='center', horizontalalignment='center',
        bbox=bbox_props, zorder=10)

# --- MODIFICA FRECCE DI ANNOTAZIONE ---
ax.annotate('', xy=(100000, c_aws_100tb), xytext=(0.655, 0.50),
            textcoords='axes fraction',
            arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.55", connectionstyle="arc3,rad=-0.08", color='#ffffff', lw=1.5),
            zorder=9)

ax.annotate('', xy=(100000, c_oci_na_100tb), xytext=(0.655, 0.40),
            textcoords='axes fraction',
            arrowprops=dict(arrowstyle="-|>,head_width=0.35,head_length=0.55", connectionstyle="arc3,rad=0.15", color='#ffffff', lw=1.5),
            zorder=9)

ax.legend(
    loc='upper left', 
    facecolor='#1c2541', 
    edgecolor='#3a506b', 
    fontsize=14, 
    handlelength=4, 
    labelcolor='#ffffff', 
    framealpha=0.95
)

fig.text(0.12, 0.015, '* Nota: Il Free Tier di AWS\nè escluso nella regione Cina.', 
         fontsize=9, color='#94a3b8', fontstyle='italic', linespacing=1.35)

plt.tight_layout()
plt.subplots_adjust(bottom=0.13)
plt.savefig('data_egress.png', dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
plt.show()