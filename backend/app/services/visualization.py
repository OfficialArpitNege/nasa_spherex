"""
Motion trail visualization service.

Generates WCS-aware (or sky-coordinate) visualizations showing
the positional change of moving-object candidates between two epochs.

Uses Matplotlib with Astropy WCSAxes for proper astronomical coordinate rendering.
"""
import logging
from pathlib import Path
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS

from app.models.motion import MovingObjectCandidate

logger = logging.getLogger(__name__)


def generate_motion_trail(
    candidates: List[MovingObjectCandidate],
    wcs_1: Optional[WCS],
    wcs_2: Optional[WCS],
    data_1: Optional[np.ndarray],
    data_2: Optional[np.ndarray],
    observation_id_1: str,
    observation_id_2: str,
    timestamp_utc_1: Optional[str],
    timestamp_utc_2: Optional[str],
    bandpass_1: Optional[str],
    bandpass_2: Optional[str],
    output_dir: Path,
    analysis_id: str = "analysis",
) -> List[str]:
    """
    Generate motion trail visualizations for moving-object candidates.

    Creates two types of plots:
    1. Sky-coordinate scatter plot showing all candidate positions and motion vectors
    2. Per-candidate side-by-side image panels (if image data available)

    Parameters:
        candidates: List of MovingObjectCandidate objects to visualize
        wcs_1, wcs_2: Astropy WCS objects for each epoch (optional)
        data_1, data_2: Science image arrays for each epoch (optional)
        observation_id_1, observation_id_2: Observation IDs
        timestamp_utc_1, timestamp_utc_2: UTC timestamps
        bandpass_1, bandpass_2: Bandpass/detector channel names
        output_dir: Directory to save generated images
        analysis_id: Unique identifier for this analysis run

    Returns:
        List of paths to generated visualization files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[str] = []

    # Filter to candidates with measurable motion (not stationary)
    motion_candidates = [
        c for c in candidates
        if c.status in ("moving-object-candidate", "possible-motion")
    ]

    if not motion_candidates:
        logger.info("No motion candidates to visualize")
        return generated_paths

    # === Plot 1: Overview sky-coordinate motion map ===
    try:
        overview_path = _generate_overview_plot(
            candidates=motion_candidates,
            observation_id_1=observation_id_1,
            observation_id_2=observation_id_2,
            timestamp_utc_1=timestamp_utc_1,
            timestamp_utc_2=timestamp_utc_2,
            bandpass_1=bandpass_1,
            bandpass_2=bandpass_2,
            output_dir=output_dir,
            analysis_id=analysis_id,
        )
        generated_paths.append(str(overview_path))
    except Exception as e:
        logger.warning("Failed to generate overview motion plot: %s", e)

    # === Plot 2: Side-by-side image panels for top candidates ===
    if data_1 is not None and data_2 is not None and wcs_1 is not None and wcs_2 is not None:
        # Limit to top 5 candidates by displacement to avoid excessive file generation
        top_candidates = sorted(
            motion_candidates,
            key=lambda c: c.angular_displacement.arcsec,
            reverse=True
        )[:5]

        for candidate in top_candidates:
            try:
                panel_path = _generate_candidate_panel(
                    candidate=candidate,
                    wcs_1=wcs_1,
                    wcs_2=wcs_2,
                    data_1=data_1,
                    data_2=data_2,
                    observation_id_1=observation_id_1,
                    observation_id_2=observation_id_2,
                    timestamp_utc_1=timestamp_utc_1,
                    timestamp_utc_2=timestamp_utc_2,
                    output_dir=output_dir,
                    analysis_id=analysis_id,
                )
                generated_paths.append(str(panel_path))
            except Exception as e:
                logger.warning(
                    "Failed to generate panel for %s: %s",
                    candidate.candidate_id, e
                )

    return generated_paths


def _generate_overview_plot(
    candidates: List[MovingObjectCandidate],
    observation_id_1: str,
    observation_id_2: str,
    timestamp_utc_1: Optional[str],
    timestamp_utc_2: Optional[str],
    bandpass_1: Optional[str],
    bandpass_2: Optional[str],
    output_dir: Path,
    analysis_id: str,
) -> Path:
    """
    Generates an overview scatter plot in RA/DEC space showing
    all motion candidates with arrows indicating motion direction and magnitude.
    """
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)

    # Set dark background for astronomical aesthetic
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    # Collect all positions
    ras_1 = [c.position_epoch_1.ra for c in candidates]
    decs_1 = [c.position_epoch_1.dec for c in candidates]
    ras_2 = [c.position_epoch_2.ra for c in candidates]
    decs_2 = [c.position_epoch_2.dec for c in candidates]

    # Determine plot extent
    all_ra = ras_1 + ras_2
    all_dec = decs_1 + decs_2
    ra_center = np.mean(all_ra)
    dec_center = np.mean(all_dec)
    ra_range = max(np.ptp(all_ra), 0.01)
    dec_range = max(np.ptp(all_dec), 0.01)
    margin = max(ra_range, dec_range) * 0.3

    # Plot each candidate motion vector
    for candidate in candidates:
        p1 = candidate.position_epoch_1
        p2 = candidate.position_epoch_2

        # Color by status
        if candidate.status == "moving-object-candidate":
            color = "#e94560"  # Red for candidates
            marker_size = 80
        else:
            color = "#f5a623"  # Orange for possible motion
            marker_size = 50

        # Epoch 1 position
        ax.scatter(p1.ra, p1.dec, c=color, s=marker_size, marker="o",
                   edgecolors="white", linewidths=0.5, zorder=5, alpha=0.9)

        # Epoch 2 position
        ax.scatter(p2.ra, p2.dec, c=color, s=marker_size, marker="s",
                   edgecolors="white", linewidths=0.5, zorder=5, alpha=0.9)

        # Motion arrow
        dra = p2.ra - p1.ra
        ddec = p2.dec - p1.dec
        ax.annotate(
            "",
            xy=(p2.ra, p2.dec),
            xytext=(p1.ra, p1.dec),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.5, alpha=0.8),
            zorder=4
        )

        # Label
        label_text = f"{candidate.candidate_id}\n{candidate.angular_displacement.arcsec:.1f}\""
        ax.annotate(
            label_text,
            xy=(p1.ra, p1.dec),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=7,
            color="white",
            alpha=0.8,
            zorder=6
        )

    # Axes styling (RA increases to the left in astronomy convention)
    ax.invert_xaxis()
    ax.set_xlabel("Right Ascension (degrees, J2000)", fontsize=11, color="white")
    ax.set_ylabel("Declination (degrees, J2000)", fontsize=11, color="white")
    ax.tick_params(colors="white", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#4a4a6a")
    ax.grid(True, alpha=0.2, color="white", linestyle="--", linewidth=0.5)

    # Title
    date1_label = (timestamp_utc_1 or "Unknown")[:10]
    date2_label = (timestamp_utc_2 or "Unknown")[:10]
    band1_label = bandpass_1 or "Unknown band"
    band2_label = bandpass_2 or "Unknown band"

    title_lines = [
        "SPHEREx Moving Object Explorer — Motion Trail Overview",
        f"Epoch 1: {observation_id_1} ({date1_label}, {band1_label})",
        f"Epoch 2: {observation_id_2} ({date2_label}, {band2_label})",
        f"{len(candidates)} motion candidate(s)"
    ]
    ax.set_title("\n".join(title_lines), fontsize=10, color="white", pad=12, linespacing=1.4)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor="#e94560", edgecolor="white", label="Moving-object candidate"),
        mpatches.Patch(facecolor="#f5a623", edgecolor="white", label="Possible motion"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
                   markersize=8, linestyle="None", label="Epoch 1 position"),
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor="gray",
                   markersize=8, linestyle="None", label="Epoch 2 position"),
    ]
    legend = ax.legend(
        handles=legend_elements, loc="upper left", fontsize=8,
        facecolor="#1a1a2e", edgecolor="#4a4a6a", labelcolor="white"
    )

    # Disclaimer
    fig.text(
        0.5, 0.01,
        "DISCLAIMER: These are moving-object candidates only. "
        "Results require independent scientific validation.",
        ha="center", fontsize=7, color="#888888", style="italic"
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    output_path = output_dir / f"{analysis_id}_motion_overview.png"
    fig.savefig(output_path, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    logger.info("Generated motion overview plot: %s", output_path)
    return output_path


def _generate_candidate_panel(
    candidate: MovingObjectCandidate,
    wcs_1: WCS,
    wcs_2: WCS,
    data_1: np.ndarray,
    data_2: np.ndarray,
    observation_id_1: str,
    observation_id_2: str,
    timestamp_utc_1: Optional[str],
    timestamp_utc_2: Optional[str],
    output_dir: Path,
    analysis_id: str,
) -> Path:
    """
    Generates a side-by-side panel showing the candidate's location
    in both epoch images with motion vector overlay.
    """
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 6), dpi=150,
        subplot_kw={"projection": wcs_1}  # Use epoch 1 WCS for both panels
    )

    fig.patch.set_facecolor("#1a1a2e")

    p1 = candidate.position_epoch_1
    p2 = candidate.position_epoch_2

    # Image stretch
    for ax, data, obs_id, ts, pos, epoch_label in [
        (ax1, data_1, observation_id_1, timestamp_utc_1, p1, "Epoch 1"),
        (ax2, data_2, observation_id_2, timestamp_utc_2, p2, "Epoch 2"),
    ]:
        ax.set_facecolor("#16213e")
        valid = data[np.isfinite(data)]
        if len(valid) > 0:
            try:
                interval = ZScaleInterval()
                vmin, vmax = interval.get_limits(valid)
            except Exception:
                vmin = float(np.percentile(valid, 1))
                vmax = float(np.percentile(valid, 99))
        else:
            vmin, vmax = 0.0, 1.0

        if vmin >= vmax:
            vmax = vmin + 1.0

        ax.imshow(data, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)

        # Mark source position (in pixel coords for this epoch's WCS)
        ax.plot(
            pos.x, pos.y,
            marker="+", color="cyan", markersize=18, markeredgewidth=2,
            zorder=10
        )

        # Circle around source
        circle = plt.Circle(
            (pos.x, pos.y), radius=3, fill=False,
            color="cyan", linewidth=1.5, linestyle="--", zorder=9
        )
        ax.add_patch(circle)

        # Title
        date_label = (ts or "Unknown")[:19]
        ax.set_title(
            f"{epoch_label}: {obs_id}\n{date_label}",
            fontsize=9, color="white", pad=8
        )

        try:
            ax.coords.grid(color="white", alpha=0.25, linestyle="--", linewidth=0.5)
            ax.coords["ra"].set_axislabel("RA (J2000)", fontsize=8, color="white")
            ax.coords["dec"].set_axislabel("DEC (J2000)", fontsize=8, color="white")
            ax.coords["ra"].set_major_formatter("d.ddd")
            ax.coords["dec"].set_major_formatter("d.ddd")
            ax.coords["ra"].set_ticklabel(size=7, color="white")
            ax.coords["dec"].set_ticklabel(size=7, color="white")
        except Exception:
            pass

    # Overall title with candidate info
    fig.suptitle(
        f"SPHEREx {candidate.candidate_id} — {candidate.status}\n"
        f"Displacement: {candidate.angular_displacement.arcsec:.2f}\" "
        f"| Speed: {candidate.average_angular_speed.arcsec_per_day:.2f}\"/day "
        f"| Direction: {candidate.direction_label} (PA={candidate.position_angle_deg:.1f}°)",
        fontsize=10, color="white", y=1.02
    )

    # Disclaimer
    fig.text(
        0.5, -0.02,
        "Moving-object candidate — requires independent scientific validation",
        ha="center", fontsize=7, color="#888888", style="italic"
    )

    plt.tight_layout()
    output_path = output_dir / f"{analysis_id}_{candidate.candidate_id}_panel.png"
    fig.savefig(
        output_path, format="png", bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )
    plt.close(fig)

    logger.info("Generated candidate panel: %s", output_path)
    return output_path
