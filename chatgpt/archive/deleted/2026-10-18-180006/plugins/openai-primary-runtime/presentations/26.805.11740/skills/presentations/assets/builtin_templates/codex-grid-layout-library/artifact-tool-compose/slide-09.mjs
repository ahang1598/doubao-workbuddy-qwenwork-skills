import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide09Tokens = contentTokens["slide-09"];

export function buildSlide09(presentation, tokens = slide09Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-09", width: "fill", height: "fill" }, [
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
    top: 36.17
  },
  width: 1197.33,
  height: 134.7,
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
      shape({
  name: "Rounded-Rectangle-9-4",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 452.38,
    top: 353.33
  },
  width: 374.67,
  height: 276
}),
      shape({
  name: "Rounded-Rectangle-10-5",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 864,
    top: 353.33
  },
  width: 374.67,
  height: 276
}),
      text([tokens.body3.titleHere, tokens.body3.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-9-6",
  position: {
    left: 485.23,
    top: 435.29
  },
  width: 309.64,
  height: 150.43,
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
      text([tokens.body4.titleHere, tokens.body4.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-10-7",
  position: {
    left: 896.18,
    top: 435.29
  },
  width: 309.64,
  height: 150.43,
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
  name: "Google-Shape-340-p61-8",
  geometry: "custom",
  customPaths: [
    {
      width: 21600,
      height: 21600,
      commands: [
        {
          moveTo: {
            x: 10800,
            y: 2160
          }
        },
        {
          cubicBezTo: {
            x1: 6029,
            y1: 2160,
            x2: 2160,
            y2: 6029,
            x: 2160,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 2160,
            y1: 15571,
            x2: 6029,
            y2: 19440,
            x: 10800,
            y: 19440
          }
        },
        {
          cubicBezTo: {
            x1: 15571,
            y1: 19440,
            x2: 19440,
            y2: 15571,
            x: 19440,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 19440,
            y1: 6029,
            x2: 15571,
            y2: 2160,
            x: 10800,
            y: 2160
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 0,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 4835,
            x2: 4835,
            y2: 0,
            x: 10800,
            y: 0
          }
        },
        {
          cubicBezTo: {
            x1: 16765,
            y1: 0,
            x2: 21600,
            y2: 4835,
            x: 21600,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 16765,
            x2: 16765,
            y2: 21600,
            x: 10800,
            y: 21600
          }
        },
        {
          cubicBezTo: {
            x1: 4835,
            y1: 21600,
            x2: 0,
            y2: 16765,
            x: 0,
            y: 10800
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 15201,
            y: 6407
          }
        },
        {
          cubicBezTo: {
            x1: 15689,
            y1: 6750,
            x2: 15807,
            y2: 7424,
            x: 15463,
            y: 7911
          }
        },
        {
          lineTo: {
            x: 10333,
            y: 15201
          }
        },
        {
          cubicBezTo: {
            x1: 10144,
            y1: 15470,
            x2: 9844,
            y2: 15637,
            x: 9517,
            y: 15658
          }
        },
        {
          cubicBezTo: {
            x1: 9190,
            y1: 15678,
            x2: 8871,
            y2: 15549,
            x: 8651,
            y: 15307
          }
        },
        {
          lineTo: {
            x: 5951,
            y: 12337
          }
        },
        {
          cubicBezTo: {
            x1: 5550,
            y1: 11895,
            x2: 5583,
            y2: 11213,
            x: 6023,
            y: 10811
          }
        },
        {
          cubicBezTo: {
            x1: 6465,
            y1: 10410,
            x2: 7147,
            y2: 10443,
            x: 7549,
            y: 10883
          }
        },
        {
          lineTo: {
            x: 9342,
            y: 12856
          }
        },
        {
          lineTo: {
            x: 13697,
            y: 6669
          }
        },
        {
          cubicBezTo: {
            x1: 14040,
            y1: 6181,
            x2: 14714,
            y2: 6063,
            x: 15201,
            y: 6407
          }
        },
        {
          close: {}
        }
      ]
    }
  ],
  fill: "#000000",
  position: {
    left: 485.84,
    top: 387.83
  },
  width: 24.55,
  height: 24.54
}),
      shape({
  name: "Google-Shape-340-p61-9",
  geometry: "custom",
  customPaths: [
    {
      width: 21600,
      height: 21600,
      commands: [
        {
          moveTo: {
            x: 10800,
            y: 2160
          }
        },
        {
          cubicBezTo: {
            x1: 6029,
            y1: 2160,
            x2: 2160,
            y2: 6029,
            x: 2160,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 2160,
            y1: 15571,
            x2: 6029,
            y2: 19440,
            x: 10800,
            y: 19440
          }
        },
        {
          cubicBezTo: {
            x1: 15571,
            y1: 19440,
            x2: 19440,
            y2: 15571,
            x: 19440,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 19440,
            y1: 6029,
            x2: 15571,
            y2: 2160,
            x: 10800,
            y: 2160
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 0,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 4835,
            x2: 4835,
            y2: 0,
            x: 10800,
            y: 0
          }
        },
        {
          cubicBezTo: {
            x1: 16765,
            y1: 0,
            x2: 21600,
            y2: 4835,
            x: 21600,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 16765,
            x2: 16765,
            y2: 21600,
            x: 10800,
            y: 21600
          }
        },
        {
          cubicBezTo: {
            x1: 4835,
            y1: 21600,
            x2: 0,
            y2: 16765,
            x: 0,
            y: 10800
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 15201,
            y: 6407
          }
        },
        {
          cubicBezTo: {
            x1: 15689,
            y1: 6750,
            x2: 15807,
            y2: 7424,
            x: 15463,
            y: 7911
          }
        },
        {
          lineTo: {
            x: 10333,
            y: 15201
          }
        },
        {
          cubicBezTo: {
            x1: 10144,
            y1: 15470,
            x2: 9844,
            y2: 15637,
            x: 9517,
            y: 15658
          }
        },
        {
          cubicBezTo: {
            x1: 9190,
            y1: 15678,
            x2: 8871,
            y2: 15549,
            x: 8651,
            y: 15307
          }
        },
        {
          lineTo: {
            x: 5951,
            y: 12337
          }
        },
        {
          cubicBezTo: {
            x1: 5550,
            y1: 11895,
            x2: 5583,
            y2: 11213,
            x: 6023,
            y: 10811
          }
        },
        {
          cubicBezTo: {
            x1: 6465,
            y1: 10410,
            x2: 7147,
            y2: 10443,
            x: 7549,
            y: 10883
          }
        },
        {
          lineTo: {
            x: 9342,
            y: 12856
          }
        },
        {
          lineTo: {
            x: 13697,
            y: 6669
          }
        },
        {
          cubicBezTo: {
            x1: 14040,
            y1: 6181,
            x2: 14714,
            y2: 6063,
            x: 15201,
            y: 6407
          }
        },
        {
          close: {}
        }
      ]
    }
  ],
  fill: "#000000",
  position: {
    left: 895.88,
    top: 387.83
  },
  width: 24.55,
  height: 24.54
}),
      shape({
  name: "Rounded-Rectangle-5-10",
  geometry: "roundRect",
  fill: "#F2F2F2",
  position: {
    left: 40.77,
    top: 353.33
  },
  width: 374.67,
  height: 276
}),
      text([tokens.body2.titleHere, tokens.body2.loremIpsumDolorSitAmetConsecteturAdipiscing], {
  name: "Content-Placeholder-9-11",
  position: {
    left: 73.61,
    top: 435.29
  },
  width: 309.64,
  height: 150.43,
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
  name: "Google-Shape-340-p61-12",
  geometry: "custom",
  customPaths: [
    {
      width: 21600,
      height: 21600,
      commands: [
        {
          moveTo: {
            x: 10800,
            y: 2160
          }
        },
        {
          cubicBezTo: {
            x1: 6029,
            y1: 2160,
            x2: 2160,
            y2: 6029,
            x: 2160,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 2160,
            y1: 15571,
            x2: 6029,
            y2: 19440,
            x: 10800,
            y: 19440
          }
        },
        {
          cubicBezTo: {
            x1: 15571,
            y1: 19440,
            x2: 19440,
            y2: 15571,
            x: 19440,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 19440,
            y1: 6029,
            x2: 15571,
            y2: 2160,
            x: 10800,
            y: 2160
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 0,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 4835,
            x2: 4835,
            y2: 0,
            x: 10800,
            y: 0
          }
        },
        {
          cubicBezTo: {
            x1: 16765,
            y1: 0,
            x2: 21600,
            y2: 4835,
            x: 21600,
            y: 10800
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 16765,
            x2: 16765,
            y2: 21600,
            x: 10800,
            y: 21600
          }
        },
        {
          cubicBezTo: {
            x1: 4835,
            y1: 21600,
            x2: 0,
            y2: 16765,
            x: 0,
            y: 10800
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 15201,
            y: 6407
          }
        },
        {
          cubicBezTo: {
            x1: 15689,
            y1: 6750,
            x2: 15807,
            y2: 7424,
            x: 15463,
            y: 7911
          }
        },
        {
          lineTo: {
            x: 10333,
            y: 15201
          }
        },
        {
          cubicBezTo: {
            x1: 10144,
            y1: 15470,
            x2: 9844,
            y2: 15637,
            x: 9517,
            y: 15658
          }
        },
        {
          cubicBezTo: {
            x1: 9190,
            y1: 15678,
            x2: 8871,
            y2: 15549,
            x: 8651,
            y: 15307
          }
        },
        {
          lineTo: {
            x: 5951,
            y: 12337
          }
        },
        {
          cubicBezTo: {
            x1: 5550,
            y1: 11895,
            x2: 5583,
            y2: 11213,
            x: 6023,
            y: 10811
          }
        },
        {
          cubicBezTo: {
            x1: 6465,
            y1: 10410,
            x2: 7147,
            y2: 10443,
            x: 7549,
            y: 10883
          }
        },
        {
          lineTo: {
            x: 9342,
            y: 12856
          }
        },
        {
          lineTo: {
            x: 13697,
            y: 6669
          }
        },
        {
          cubicBezTo: {
            x1: 14040,
            y1: 6181,
            x2: 14714,
            y2: 6063,
            x: 15201,
            y: 6407
          }
        },
        {
          close: {}
        }
      ]
    }
  ],
  fill: "#000000",
  position: {
    left: 74.23,
    top: 387.83
  },
  width: 24.55,
  height: 24.54
}),
      text([tokens.body1.topic, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing, tokens.body1.loremIpsumDolorSitAmetConsecteturAdipiscing2], {
  name: "Content-Placeholder-15-13",
  position: {
    left: 41.33,
    top: 152.29
  },
  width: 1197.33,
  height: 171.05,
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
