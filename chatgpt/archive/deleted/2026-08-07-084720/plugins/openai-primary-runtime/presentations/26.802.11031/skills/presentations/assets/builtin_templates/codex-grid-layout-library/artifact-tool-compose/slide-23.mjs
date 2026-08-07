import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide23Tokens = contentTokens["slide-23"];

export function buildSlide23(presentation, tokens = slide23Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-23", width: "fill", height: "fill" }, [
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
  name: "Title-7-3",
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
  name: "Rounded-Rectangle-4-4",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 41.33,
    top: 213.33
  },
  width: 374.67,
  height: 416
}),
      text([tokens.label1], {
  name: "Content-Placeholder-8-5",
  position: {
    left: 67.58,
    top: 502.29
  },
  width: 322.17,
  height: 22.29,
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
      text([tokens.stat1], {
  name: "Content-Placeholder-8-6",
  position: {
    left: 67.58,
    top: 554.56
  },
  width: 179.08,
  height: 50.59,
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
      text([tokens.label4], {
  name: "Content-Placeholder-8-7",
  position: {
    left: 246.67,
    top: 569.53
  },
  width: 143.08,
  height: 22.29,
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
  name: "Rounded-Rectangle-1-9",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 452,
    top: 213.33
  },
  width: 374.67,
  height: 416
}),
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-10",
  position: {
    left: 478.25,
    top: 243.15
  },
  width: 322.17,
  height: 214.18,
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
      text([tokens.label2], {
  name: "Content-Placeholder-8-11",
  position: {
    left: 478.25,
    top: 502.29
  },
  width: 322.17,
  height: 22.29,
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
  name: "Content-Placeholder-8-12",
  position: {
    left: 478.25,
    top: 554.56
  },
  width: 179.08,
  height: 50.59,
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
      text([tokens.label5], {
  name: "Content-Placeholder-8-13",
  position: {
    left: 657.33,
    top: 569.53
  },
  width: 143.08,
  height: 22.29,
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
  name: "Rounded-Rectangle-12-15",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 862.67,
    top: 213.33
  },
  width: 374.67,
  height: 416
}),
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-16",
  position: {
    left: 888.92,
    top: 243.15
  },
  width: 322.17,
  height: 214.18,
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
      text([tokens.label3], {
  name: "Content-Placeholder-8-17",
  position: {
    left: 888.92,
    top: 502.29
  },
  width: 322.17,
  height: 22.29,
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
      text([tokens.stat3], {
  name: "Content-Placeholder-8-18",
  position: {
    left: 888.92,
    top: 554.56
  },
  width: 179.08,
  height: 50.59,
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
      text([tokens.label6], {
  name: "Content-Placeholder-8-19",
  position: {
    left: 1068,
    top: 569.53
  },
  width: 143.08,
  height: 22.29,
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
      text([tokens.body1.titleHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-8-21",
  position: {
    left: 67.42,
    top: 243.17
  },
  width: 322.33,
  height: 214.17,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    autoFit: "none",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
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
