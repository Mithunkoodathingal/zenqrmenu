import { useEffect, useRef } from "react";
import QRCodeStyling, { type Options } from "qr-code-styling";
import zenLogo from "@/assets/zen-logo.png";

export type QRStyle = "minimal" | "dark" | "instagram" | "gold";

export const getQRColors = (style: QRStyle) => {
  switch (style) {
    case "minimal":
      return { fg: "#EA580C", bg: "#FFF7ED" };
    case "dark":
      return { fg: "#38BDF8", bg: "#0C0A1A" };
    case "instagram":
      return { fg: "#833ab4", bg: "#ffffff" };
    case "gold":
      return { fg: "#FFD700", bg: "#111111" };
  }
};

const getQROptions = (style: QRStyle, value: string, size: number): Options => {
  const colors = getQRColors(style);
  const base: Options = {
    type: "canvas",
    width: size,
    height: size,
    data: value,
    margin: size > 100 ? 8 : 4,
    qrOptions: { errorCorrectionLevel: size > 100 ? "H" : "L" },
    imageOptions: {
      crossOrigin: "anonymous",
      margin: size > 100 ? 4 : 2,
      imageSize: 0.3,
      hideBackgroundDots: true,
    },
    image: size > 60 ? zenLogo : undefined,
    dotsOptions: {
      color: colors.fg,
      type: "rounded",
    },
    cornersSquareOptions: {
      color: colors.fg,
      type: "extra-rounded",
    },
    cornersDotOptions: {
      color: colors.fg,
      type: "dot",
    },
    backgroundOptions: {
      color: colors.bg,
    },
  };

  if (style === "instagram") {
    base.dotsOptions = {
      type: "dots",
      gradient: {
        type: "linear",
        rotation: Math.PI / 4,
        colorStops: [
          { offset: 0, color: "#f9ce34" },
          { offset: 0.5, color: "#ee2a7b" },
          { offset: 1, color: "#6228d7" },
        ],
      },
    };
    base.cornersSquareOptions = {
      type: "extra-rounded",
      gradient: {
        type: "linear",
        rotation: Math.PI / 4,
        colorStops: [
          { offset: 0, color: "#ee2a7b" },
          { offset: 1, color: "#6228d7" },
        ],
      },
    };
    base.cornersDotOptions = {
      type: "dot",
      gradient: {
        type: "linear",
        rotation: Math.PI / 4,
        colorStops: [
          { offset: 0, color: "#f9ce34" },
          { offset: 1, color: "#ee2a7b" },
        ],
      },
    };
    base.backgroundOptions = { color: "#ffffff" };
  }

  if (style === "dark") {
    base.dotsOptions = { type: "classy-rounded", color: "#38BDF8" };
    base.cornersSquareOptions = { type: "extra-rounded", color: "#818CF8" };
    base.cornersDotOptions = { type: "dot", color: "#38BDF8" };
  }

  if (style === "gold") {
    base.dotsOptions = {
      type: "classy-rounded",
      gradient: {
        type: "linear",
        rotation: Math.PI / 4,
        colorStops: [
          { offset: 0, color: "#FFD700" },
          { offset: 1, color: "#FFA500" },
        ],
      },
    };
    base.cornersSquareOptions = { type: "extra-rounded", color: "#FFD700" };
    base.cornersDotOptions = { type: "dot", color: "#FFA500" };
  }

  return base;
};

interface StyledQRCodeProps {
  value: string;
  size: number;
  style: QRStyle;
  className?: string;
}

const StyledQRCode = ({ value, size, style, className }: StyledQRCodeProps) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const options = getQROptions(style, value, size);
    const qr = new QRCodeStyling(options);
    ref.current.innerHTML = "";
    qr.append(ref.current);

    return () => {
      if (ref.current) {
        ref.current.innerHTML = "";
      }
    };
  }, [value, size, style]);

  return <div ref={ref} className={className} style={{ width: size, height: size, display: "flex", alignItems: "center", justifyContent: "center" }} />;
};

export const downloadStyledQR = async (
  value: string,
  style: QRStyle,
  filename: string
) => {
  const options = getQROptions(style, value, 512);
  const qr = new QRCodeStyling(options);
  await qr.download({ name: filename, extension: "png" });
};

export default StyledQRCode;
