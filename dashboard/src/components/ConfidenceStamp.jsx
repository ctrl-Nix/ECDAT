import React from "react";
import PropTypes from "prop-types";
import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";

export function ConfidenceStamp({ band, score, signals }) {
  const normalizedBand = (band || "UNVERIFIED").toUpperCase();

  const config = {
    VERIFIED: {
      label: "Verified",
      icon: ShieldCheck,
      classes: "bg-green-10 text-green border-border",
    },
    PROBABLE: {
      label: "Probable",
      icon: ShieldAlert,
      classes: "bg-surface-h text-medium border-border",
    },
    UNVERIFIED: {
      label: "Unverified",
      icon: ShieldQuestion,
      classes: "bg-surface text-t3 border-border",
    },
  }[normalizedBand] || {
    label: "Unverified",
    icon: ShieldQuestion,
    classes: "bg-surface text-t3 border-border",
  };

  const IconComponent = config.icon;
  const scoreText = score !== null && score !== undefined ? ` (${Math.round(score * 100)}%)` : "";
  const tooltip = signals && signals.length > 0 ? `Signals: ${signals.join(", ")}` : undefined;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-medium font-sans ${config.classes}`}
      title={tooltip}
    >
      <IconComponent className="h-3.5 w-3.5" />
      <span>
        {config.label}
        {scoreText}
      </span>
    </span>
  );
}

ConfidenceStamp.propTypes = {
  band: PropTypes.oneOf(["VERIFIED", "PROBABLE", "UNVERIFIED"]).isRequired,
  score: PropTypes.number,
  signals: PropTypes.arrayOf(PropTypes.string),
};

ConfidenceStamp.defaultProps = {
  score: null,
  signals: [],
};

export default ConfidenceStamp;
