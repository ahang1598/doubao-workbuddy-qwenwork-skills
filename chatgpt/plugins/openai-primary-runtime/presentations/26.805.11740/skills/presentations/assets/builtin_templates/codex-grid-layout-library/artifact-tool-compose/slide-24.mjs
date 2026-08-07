import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide24Tokens = contentTokens["slide-24"];

export function buildSlide24(presentation, tokens = slide24Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-24", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Google-Shape-532-p58-2",
  position: {
    left: 1184.18,
    top: 659.24
  },
  width: 54.48,
  height: 25.33,
  style: {
    fontSize: "13.33px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "right",
    verticalAlignment: "bottom",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.title], {
  name: "Google-Shape-533-p58-3",
  position: {
    left: 41.33,
    top: 36.12
  },
  width: 1197.33,
  height: 109.97,
  style: {
    fontSize: "38.67px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "top",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      table({
  name: "Google-Shape-953-p80-4",
  rows: 1,
  columns: 5,
  values: [
    [
      "Milestone",
      "Milestone",
      "Milestone",
      "Milestone",
      "Milestone"
    ]
  ],
  columnWidths: [
    239.47,
    239.47,
    239.47,
    239.47,
    239.47
  ],
  position: {
    left: 41.33,
    top: 144.87
  },
  width: 1197.34,
  height: 484.46
}),
      shape({
  name: "Google-Shape-955-p80-5",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 495.72,
    top: 431.26
  },
  width: 479.02,
  height: 53.89
}),
      text([tokens.label4], {
  name: "Google-Shape-955-p80-5",
  position: {
    left: 495.72,
    top: 431.26
  },
  width: 479.02,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
      shape({
  name: "Google-Shape-957-p80-6",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 61.32,
    top: 575.16
  },
  width: 1157.66,
  height: 53.89
}),
      text([tokens.label6], {
  name: "Google-Shape-957-p80-6",
  position: {
    left: 61.32,
    top: 575.16
  },
  width: 1157.66,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
      shape({
  name: "Google-Shape-960-p80-7",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 789.79,
    top: 499.21
  },
  width: 429.19,
  height: 53.89
}),
      text([tokens.label5], {
  name: "Google-Shape-960-p80-7",
  position: {
    left: 789.79,
    top: 499.21
  },
  width: 429.19,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
      shape({
  name: "Google-Shape-963-p80-8",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 296.06,
    top: 357.29
  },
  width: 922.92,
  height: 53.89
}),
      text([tokens.label3], {
  name: "Google-Shape-963-p80-8",
  position: {
    left: 296.06,
    top: 357.29
  },
  width: 922.92,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
      shape({
  name: "Google-Shape-966-p80-9",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 296.06,
    top: 283.31
  },
  width: 672.81,
  height: 53.89
}),
      text([tokens.label2], {
  name: "Google-Shape-966-p80-9",
  position: {
    left: 296.06,
    top: 283.31
  },
  width: 672.81,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-10",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 53.32,
    top: 207.36
  },
  width: 439.39,
  height: 53.89
}),
      text([tokens.label1], {
  name: "Google-Shape-969-p80-10",
  position: {
    left: 53.32,
    top: 207.36
  },
  width: 439.39,
  height: 53.89,
  style: {
    fontSize: "24px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "middle",
    autoFit: "none",
    wrap: "square",
    insets: {
      top: 12.8,
      right: 12.8,
      bottom: 12.8,
      left: 22.08
    }
  }
}),
    ]),
    { frame: {
  left: 0,
  top: 0,
  width: 1280,
  height: 720
}, baseUnit: 1 },
  );
  return slide;
}
