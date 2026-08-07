import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide16Tokens = contentTokens["slide-16"];

export function buildSlide16(presentation, tokens = slide16Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-16", width: "fill", height: "fill" }, [
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
      text([tokens.body5.titleHere, tokens.body5.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-15-4",
  position: {
    left: 41.33,
    top: 436.86
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "21.33px",
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
      text([tokens.body6.titleHere, tokens.body6.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-16-5",
  position: {
    left: 350.13,
    top: 436.86
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "24px",
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
      text([tokens.body7.titleHere, tokens.body7.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-17-6",
  position: {
    left: 657.68,
    top: 436.86
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "21.33px",
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
      text([tokens.body8.titleHere, tokens.body8.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-18-7",
  position: {
    left: 966.48,
    top: 436.86
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "24px",
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
  name: "Content-Placeholder-15-8",
  position: {
    left: 41.33,
    top: 231.82
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "21.33px",
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
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-16-9",
  position: {
    left: 350.13,
    top: 231.82
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "24px",
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
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-17-10",
  position: {
    left: 657.68,
    top: 231.82
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "21.33px",
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
      text([tokens.body4.titleHere, tokens.body4.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Text-Placeholder-18-11",
  position: {
    left: 966.48,
    top: 231.82
  },
  width: 272.54,
  height: 148.62,
  style: {
    fontSize: "24px",
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
  return slide;
}
