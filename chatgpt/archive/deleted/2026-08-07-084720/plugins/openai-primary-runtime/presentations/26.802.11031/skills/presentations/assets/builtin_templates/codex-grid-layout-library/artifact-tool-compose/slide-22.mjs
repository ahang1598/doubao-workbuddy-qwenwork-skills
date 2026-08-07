import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide22Tokens = contentTokens["slide-22"];

export function buildSlide22(presentation, tokens = slide22Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-22", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Slide-Number-Placeholder-3-2",
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
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.title], {
  name: "Title-10-3",
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
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.stat1], {
  name: "Content-Placeholder-9-4",
  position: {
    left: 668.36,
    top: 427.54
  },
  width: 223.97,
  height: 94.88,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.body2], {
  name: "Content-Placeholder-15-5",
  position: {
    left: 675.36,
    top: 532.1
  },
  width: 216.98,
  height: 64.67,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.stat2], {
  name: "Content-Placeholder-9-6",
  position: {
    left: 978.31,
    top: 427.54
  },
  width: 223.97,
  height: 94.88,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    verticalAlignment: "bottom",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      text([tokens.body3], {
  name: "Content-Placeholder-15-7",
  position: {
    left: 985.3,
    top: 532.1
  },
  width: 216.98,
  height: 64.67,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
    }
  }
}),
      shape({
  name: "Rounded-Rectangle-1-8",
  geometry: "roundRect",
  fill: "none",
  line: {
    style: "solid",
    width: 1.33,
    fill: "#000000"
  },
  position: {
    left: 41.33,
    top: 109.33
  },
  width: 580.19,
  height: 570.61
}),
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-1-9",
  position: {
    left: 675.36,
    top: 179.45
  },
  width: 559.75,
  height: 169.46,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "shrinkText",
    insets: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0
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
  slide.charts.add("bar", {
  position: {
    left: 66.61,
    top: 138.84,
    width: 528.06,
    height: 502.32
  },
  categories: [
    "Category 1",
    "Category 2",
    "Category 3",
    "Category 4"
  ],
  series: [
    {
      name: "Series 1",
      categories: [
        "Category 1",
        "Category 2",
        "Category 3",
        "Category 4"
      ],
      values: [
        1.6,
        2.2,
        3.5,
        5.8
      ],
      fill: "#6DCBF4"
    },
    {
      name: "Series 2",
      categories: [
        "Category 1",
        "Category 2",
        "Category 3",
        "Category 4"
      ],
      values: [
        1.7,
        2.4,
        5,
        8
      ],
      fill: "#3D8DFF"
    }
  ],
  hasLegend: true,
  legend: {
    position: "bottom",
    overlay: false
  },
  dataLabels: {
    showValue: true
  },
  chartFill: "#FFFFFF",
  chartLine: {
    style: "solid",
    width: 0,
    fill: "#FFFFFF"
  },
  plotAreaFill: {
    type: "none"
  },
  plotAreaLine: {
    style: "solid",
    width: 0,
    fill: "#FFFFFF"
  },
  xAxis: {
    visible: true,
    deleted: false,
    line: {
      style: "solid",
      width: 1,
      fill: "#B8BCC4"
    },
    textStyle: {
      typeface: "Helvetica Neue",
      fontSize: "11px",
      color: "#000000"
    }
  },
  yAxis: {
    visible: true,
    deleted: false,
    max: 8,
    majorUnit: 2,
    majorGridlines: {
      style: "solid",
      width: 1,
      fill: "#EDEDED"
    },
    line: {
      style: "solid",
      width: 0,
      fill: "#FFFFFF"
    },
    textStyle: {
      typeface: "Helvetica Neue",
      fontSize: "11px",
      color: "#000000"
    }
  },
  barOptions: {
    direction: "column",
    grouping: "clustered",
    gapWidth: 100
  }
});
  return slide;
}
