from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent.parent
x=np.linspace(-12,12,1201)
fig,axes=plt.subplots(3,2,figsize=(11,10),constrained_layout=True)
for sigma in (1,2,4):
    g=np.exp(-x*x/(2*sigma*sigma))/(np.sqrt(2*np.pi)*sigma)
    curves=(g,-x*g/sigma**2,(x*x/sigma**4-1/sigma**2)*g)
    for order,y in enumerate(curves):
        axes[order,0].plot(x,y,label=f"sigma={sigma}")
        axes[order,1].plot(x,sigma**order*y,label=f"sigma={sigma}")
for order in range(3):
    for j in range(2):
        axes[order,j].axhline(0,color="gray",lw=.6)
        axes[order,j].set_title(f"Order {order}: "+("raw" if j==0 else "scale normalized"))
        axes[order,j].set_xlabel("x (pixel)")
        axes[order,j].set_ylabel("Kernel value")
        axes[order,j].grid(alpha=.2)
        axes[order,j].legend()
fig.savefig(root/"figures/theory_gaussian_derivatives.png",dpi=300)
plt.close(fig)
sigmas=np.linspace(.25,12,1200)
fig,ax=plt.subplots(figsize=(7,4),constrained_layout=True)
for s in (2,4,6):
    response=2*s*s*sigmas**2/(s*s+sigmas**2)**2
    ax.plot(sigmas,response,label=f"Gaussian blob s={s}")
    ax.scatter([s],[.5],s=25)
ax.set(xlabel="Analysis sigma (pixel)",ylabel="Normalized |LoG| at center",
       title="Analytic scale selection, amplitude A=1")
ax.grid(alpha=.2)
ax.legend()
fig.savefig(root/"figures/theory_blob_scale_selection.png",dpi=300)
plt.close(fig)
print("Saved two analytical illustrations; these are not measured Fiji outputs.")
