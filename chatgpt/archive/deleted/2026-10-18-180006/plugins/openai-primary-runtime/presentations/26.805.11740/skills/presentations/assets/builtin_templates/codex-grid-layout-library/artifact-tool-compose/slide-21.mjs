import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide21Tokens = contentTokens["slide-21"];

export function buildSlide21(presentation, tokens = slide21Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-21", width: "fill", height: "fill" }, [
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
      shape({
  name: "Rounded-Rectangle-36-4",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 658.48,
    top: 352.76
  },
  width: 271.07,
  height: 278.9
}),
      text([tokens.stat1], {
  name: "Content-Placeholder-9-5",
  position: {
    left: 683.4,
    top: 375.85
  },
  width: 223.97,
  height: 121.35,
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
  name: "Content-Placeholder-15-6",
  position: {
    left: 690.39,
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
  name: "Rounded-Rectangle-39-7",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 968.42,
    top: 352.76
  },
  width: 271.07,
  height: 278.9
}),
      text([tokens.stat2], {
  name: "Content-Placeholder-9-8",
  position: {
    left: 993.34,
    top: 375.85
  },
  width: 223.97,
  height: 121.35,
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
  name: "Content-Placeholder-15-9",
  position: {
    left: 1000.33,
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
      text([tokens.body1], {
  name: "Content-Placeholder-2-10",
  position: {
    left: 657.33,
    top: 205.31
  },
  width: 581.61,
  height: 104,
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
    ]),
    { frame: {
  left: 0,
  top: 0,
  width: 1280,
  height: 720
}, baseUnit: 1 },
  );
  slide.charts.add("line", {
  position: {
    left: 40.51,
    top: 131.73,
    width: 581.02,
    height: 527.51
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
      line: {
        style: "solid",
        width: 3,
        fill: "#3D8DFF"
      },
      marker: {
        symbol: "circle",
        size: 6
      }
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
      line: {
        style: "solid",
        width: 3,
        fill: "#D0EDFA"
      },
      marker: {
        symbol: "circle",
        size: 6
      }
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
  lineOptions: {
    grouping: "standard"
  }
});
  return slide;
}
