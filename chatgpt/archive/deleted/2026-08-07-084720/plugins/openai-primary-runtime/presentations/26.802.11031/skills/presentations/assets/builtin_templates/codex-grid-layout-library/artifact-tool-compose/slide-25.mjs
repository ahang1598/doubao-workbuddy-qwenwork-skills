import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide25Tokens = contentTokens["slide-25"];

export function buildSlide25(presentation, tokens = slide25Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-25", width: "fill", height: "fill" }, [
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
  rows: 4,
  columns: 5,
  values: [
    [
      "",
      "",
      "",
      "",
      ""
    ],
    [
      "",
      "",
      "",
      "",
      ""
    ],
    [
      "",
      "",
      "",
      "",
      ""
    ],
    [
      "",
      "",
      "",
      "",
      ""
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
    top: 133.33
  },
  width: 1197.34,
  height: 514.67
}),
      ...["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day, index) =>
        text([day], {
          name: `weekday-${index + 1}`,
          position: { left: 41.33 + index * 239.47, top: 86.31 },
          width: 239.47,
          height: 34,
          style: {
            fontSize: "13.33px",
            typeface: "Helvetica Neue",
            color: "#000000",
            alignment: "center",
            verticalAlignment: "middle",
            insets: { top: 0, right: 0, bottom: 0, left: 0 }
          }
        })
      ),
      ...Array.from({ length: 20 }, (_, index) =>
        text(["#"], {
          name: `day-number-${index + 1}`,
          position: {
            left: 56.27 + (index % 5) * 239.47,
            top: 141.33 + Math.floor(index / 5) * 128.67
          },
          width: 30,
          height: 24,
          style: {
            fontSize: "13.33px",
            typeface: "Helvetica Neue",
            color: "#000000",
            alignment: "left",
            verticalAlignment: "top",
            insets: { top: 0, right: 0, bottom: 0, left: 0 }
          }
        })
      ),
      shape({
  name: "Google-Shape-969-p80-5",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 56.27,
    top: 171.48
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label1], {
  name: "Google-Shape-969-p80-5",
  position: {
    left: 56.27,
    top: 171.48
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-6",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 56.27,
    top: 214.15
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label3], {
  name: "Google-Shape-969-p80-6",
  position: {
    left: 56.27,
    top: 214.15
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-7",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 534.93,
    top: 187.77
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label2], {
  name: "Google-Shape-969-p80-7",
  position: {
    left: 534.93,
    top: 187.77
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-8",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 56.27,
    top: 446.98
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label4], {
  name: "Google-Shape-969-p80-8",
  position: {
    left: 56.27,
    top: 446.98
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-9",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 773.6,
    top: 446.98
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label5], {
  name: "Google-Shape-969-p80-9",
  position: {
    left: 773.6,
    top: 446.98
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
    }
  }
}),
      shape({
  name: "Google-Shape-969-p80-10",
  geometry: "roundRect",
  fill: "#D0EDFA",
  position: {
    left: 296.27,
    top: 573.1
  },
  width: 210.4,
  height: 35.69
}),
      text([tokens.label6], {
  name: "Google-Shape-969-p80-10",
  position: {
    left: 296.27,
    top: 573.1
  },
  width: 210.4,
  height: 35.69,
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
      left: 12.48
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
