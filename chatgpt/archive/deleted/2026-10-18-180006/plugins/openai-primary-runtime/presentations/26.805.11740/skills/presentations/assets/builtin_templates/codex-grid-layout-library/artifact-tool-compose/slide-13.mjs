import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide13Tokens = contentTokens["slide-13"];

export function buildSlide13(presentation, tokens = slide13Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-13", width: "fill", height: "fill" }, [
      text([tokens.footer1], {
  name: "Slide-Number-Placeholder-1-2",
  position: {
    left: 1184.17,
    top: 659.17
  },
  width: 54.5,
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
  name: "Title-2-3",
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
      text([tokens.body1.titleGoesHere, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-9-4",
  position: {
    left: 41.33,
    top: 213.33
  },
  width: 581.33,
  height: 172.5,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
    }
  }
}),
      text([tokens.body2.titleGoesHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-5",
  position: {
    left: 656.86,
    top: 213.33
  },
  width: 581.33,
  height: 172.5,
  style: {
    fontSize: "32px",
    typeface: "Helvetica Neue",
    color: "#000000",
    alignment: "left",
    insets: {
      top: 4.8,
      right: 9.6,
      bottom: 4.8,
      left: 9.6
    }
  }
}),
      text([tokens.body3.titleGoesHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-9-6",
  position: {
    left: 41.33,
    top: 421.73
  },
  width: 581.33,
  height: 172.51,
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
      text([tokens.body4.titleGoesHere, tokens.body4.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-7",
  position: {
    left: 656.86,
    top: 421.73
  },
  width: 581.33,
  height: 172.51,
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
  return slide;
}
