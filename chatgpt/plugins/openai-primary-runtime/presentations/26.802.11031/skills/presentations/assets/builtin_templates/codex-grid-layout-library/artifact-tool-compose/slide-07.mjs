import { image, layers, shape, table, text } from "@oai/artifact-tool";
import { contentTokens } from "./runtime.mjs";

export const slide07Tokens = contentTokens["slide-07"];

export function buildSlide07(presentation, tokens = slide07Tokens) {
  const slide = presentation.slides.add();
  slide.compose(
    layers({ name: "codex-grid-layout-library#slide-07", width: "fill", height: "fill" }, [
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
      text([tokens.body1], {
  name: "Google-Shape-558-p61-4",
  position: {
    left: 41.33,
    top: 421.33
  },
  width: 374.67,
  height: 208,
  style: {
    fontSize: "32px",
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
      text([tokens.body2], {
  name: "Google-Shape-559-p61-5",
  position: {
    left: 453.33,
    top: 421.33
  },
  width: 374.67,
  height: 208,
  style: {
    fontSize: "32px",
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
      text([tokens.body3], {
  name: "Google-Shape-560-p61-6",
  position: {
    left: 864.28,
    top: 421.33
  },
  width: 374.67,
  height: 208,
  style: {
    fontSize: "32px",
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
  name: "Google-Shape-561-p61-7",
  geometry: "custom",
  customPaths: [
    {
      width: 20236,
      height: 20115,
      commands: [
        {
          moveTo: {
            x: 11303,
            y: 2594
          }
        },
        {
          lineTo: {
            x: 2175,
            y: 11983
          }
        },
        {
          lineTo: {
            x: 9033,
            y: 11983
          }
        },
        {
          cubicBezTo: {
            x1: 9364,
            y1: 11983,
            x2: 9678,
            y2: 12118,
            x: 9883,
            y: 12348
          }
        },
        {
          cubicBezTo: {
            x1: 10089,
            y1: 12579,
            x2: 10165,
            y2: 12880,
            x: 10089,
            y: 13166
          }
        },
        {
          lineTo: {
            x: 8933,
            y: 17522
          }
        },
        {
          lineTo: {
            x: 18061,
            y: 8133
          }
        },
        {
          lineTo: {
            x: 11203,
            y: 8133
          }
        },
        {
          cubicBezTo: {
            x1: 10872,
            y1: 8133,
            x2: 10558,
            y2: 7999,
            x: 10353,
            y: 7768
          }
        },
        {
          cubicBezTo: {
            x1: 10147,
            y1: 7537,
            x2: 10071,
            y2: 7236,
            x: 10147,
            y: 6950
          }
        },
        {
          lineTo: {
            x: 11303,
            y: 2594
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 10382,
            y: 593
          }
        },
        {
          cubicBezTo: {
            x1: 11679,
            y1: -742,
            x2: 14125,
            y2: 363,
            x: 13670,
            y: 2078
          }
        },
        {
          lineTo: {
            x: 12574,
            y: 6208
          }
        },
        {
          lineTo: {
            x: 18061,
            y: 6208
          }
        },
        {
          cubicBezTo: {
            x1: 19918,
            y1: 6208,
            x2: 20918,
            y2: 8142,
            x: 19705,
            y: 9390
          }
        },
        {
          lineTo: {
            x: 9854,
            y: 19523
          }
        },
        {
          cubicBezTo: {
            x1: 8557,
            y1: 20858,
            x2: 6111,
            y2: 19753,
            x: 6566,
            y: 18038
          }
        },
        {
          lineTo: {
            x: 7662,
            y: 13908
          }
        },
        {
          lineTo: {
            x: 2175,
            y: 13908
          }
        },
        {
          cubicBezTo: {
            x1: 318,
            y1: 13908,
            x2: -682,
            y2: 11974,
            x: 531,
            y: 10726
          }
        },
        {
          lineTo: {
            x: 10382,
            y: 593
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
    left: 449.33,
    top: 355.1
  },
  width: 33.13,
  height: 37.15
}),
      shape({
  name: "Google-Shape-562-p61-8",
  geometry: "custom",
  customPaths: [
    {
      width: 21600,
      height: 21333,
      commands: [
        {
          moveTo: {
            x: 11359,
            y: 2130
          }
        },
        {
          cubicBezTo: {
            x1: 11014,
            y1: 1951,
            x2: 10588,
            y2: 1951,
            x: 10241,
            y: 2130
          }
        },
        {
          lineTo: {
            x: 3250,
            y: 5732
          }
        },
        {
          lineTo: {
            x: 10817,
            y: 9530
          }
        },
        {
          lineTo: {
            x: 18593,
            y: 5856
          }
        },
        {
          lineTo: {
            x: 11359,
            y: 2130
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 19364,
            y: 7749
          }
        },
        {
          lineTo: {
            x: 11918,
            y: 11267
          }
        },
        {
          lineTo: {
            x: 11918,
            y: 18916
          }
        },
        {
          lineTo: {
            x: 18805,
            y: 15367
          }
        },
        {
          cubicBezTo: {
            x1: 19152,
            y1: 15189,
            x2: 19364,
            y2: 14860,
            x: 19364,
            y: 14503
          }
        },
        {
          lineTo: {
            x: 19364,
            y: 7749
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 9682,
            y: 18916
          }
        },
        {
          lineTo: {
            x: 9682,
            y: 11250
          }
        },
        {
          lineTo: {
            x: 2236,
            y: 7513
          }
        },
        {
          lineTo: {
            x: 2236,
            y: 14503
          }
        },
        {
          cubicBezTo: {
            x1: 2236,
            y1: 14860,
            x2: 2448,
            y2: 15189,
            x: 2795,
            y: 15367
          }
        },
        {
          lineTo: {
            x: 9682,
            y: 18916
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 9123,
            y: 401
          }
        },
        {
          cubicBezTo: {
            x1: 10160,
            y1: -133,
            x2: 11440,
            y2: -133,
            x: 12477,
            y: 401
          }
        },
        {
          lineTo: {
            x: 19923,
            y: 4238
          }
        },
        {
          cubicBezTo: {
            x1: 20962,
            y1: 4773,
            x2: 21600,
            y2: 5761,
            x: 21600,
            y: 6830
          }
        },
        {
          lineTo: {
            x: 21600,
            y: 14503
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 15572,
            x2: 20962,
            y2: 16561,
            x: 19923,
            y: 17096
          }
        },
        {
          lineTo: {
            x: 12477,
            y: 20932
          }
        },
        {
          cubicBezTo: {
            x1: 11440,
            y1: 21467,
            x2: 10160,
            y2: 21467,
            x: 9123,
            y: 20932
          }
        },
        {
          lineTo: {
            x: 1677,
            y: 17096
          }
        },
        {
          cubicBezTo: {
            x1: 640,
            y1: 16561,
            x2: 0,
            y2: 15572,
            x: 0,
            y: 14503
          }
        },
        {
          lineTo: {
            x: 0,
            y: 6830
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 5761,
            x2: 640,
            y2: 4773,
            x: 1677,
            y: 4238
          }
        },
        {
          lineTo: {
            x: 9123,
            y: 401
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
    left: 42.14,
    top: 354.67
  },
  width: 34.34,
  height: 38.01
}),
      shape({
  name: "Google-Shape-563-p61-9",
  geometry: "custom",
  customPaths: [
    {
      width: 21600,
      height: 21600,
      commands: [
        {
          moveTo: {
            x: 6220,
            y: 0
          }
        },
        {
          lineTo: {
            x: 15380,
            y: 0
          }
        },
        {
          cubicBezTo: {
            x1: 16250,
            y1: 0,
            x2: 16968,
            y2: 0,
            x: 17552,
            y: 59
          }
        },
        {
          cubicBezTo: {
            x1: 18159,
            y1: 122,
            x2: 18717,
            y2: 255,
            x: 19241,
            y: 589
          }
        },
        {
          cubicBezTo: {
            x1: 20055,
            y1: 1106,
            x2: 20715,
            y2: 1932,
            x: 21129,
            y: 2948
          }
        },
        {
          cubicBezTo: {
            x1: 21396,
            y1: 3603,
            x2: 21503,
            y2: 4301,
            x: 21552,
            y: 5060
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 5790,
            x2: 21600,
            y2: 6688,
            x: 21600,
            y: 7775
          }
        },
        {
          lineTo: {
            x: 21600,
            y: 13825
          }
        },
        {
          cubicBezTo: {
            x1: 21600,
            y1: 14912,
            x2: 21600,
            y2: 15810,
            x: 21552,
            y: 16540
          }
        },
        {
          cubicBezTo: {
            x1: 21503,
            y1: 17299,
            x2: 21396,
            y2: 17997,
            x: 21129,
            y: 18652
          }
        },
        {
          cubicBezTo: {
            x1: 20715,
            y1: 19668,
            x2: 20055,
            y2: 20494,
            x: 19241,
            y: 21011
          }
        },
        {
          cubicBezTo: {
            x1: 18717,
            y1: 21345,
            x2: 18159,
            y2: 21478,
            x: 17552,
            y: 21541
          }
        },
        {
          cubicBezTo: {
            x1: 16968,
            y1: 21600,
            x2: 16250,
            y2: 21600,
            x: 15380,
            y: 21600
          }
        },
        {
          lineTo: {
            x: 6220,
            y: 21600
          }
        },
        {
          cubicBezTo: {
            x1: 5350,
            y1: 21600,
            x2: 4632,
            y2: 21600,
            x: 4048,
            y: 21541
          }
        },
        {
          cubicBezTo: {
            x1: 3441,
            y1: 21478,
            x2: 2883,
            y2: 21345,
            x: 2359,
            y: 21011
          }
        },
        {
          cubicBezTo: {
            x1: 1545,
            y1: 20494,
            x2: 885,
            y2: 19668,
            x: 471,
            y: 18652
          }
        },
        {
          cubicBezTo: {
            x1: 204,
            y1: 17997,
            x2: 97,
            y2: 17299,
            x: 48,
            y: 16540
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 15810,
            x2: 0,
            y2: 14912,
            x: 0,
            y: 13825
          }
        },
        {
          lineTo: {
            x: 0,
            y: 7775
          }
        },
        {
          cubicBezTo: {
            x1: 0,
            y1: 6688,
            x2: 0,
            y2: 5790,
            x: 48,
            y: 5060
          }
        },
        {
          cubicBezTo: {
            x1: 97,
            y1: 4301,
            x2: 204,
            y2: 3603,
            x: 471,
            y: 2948
          }
        },
        {
          cubicBezTo: {
            x1: 885,
            y1: 1932,
            x2: 1545,
            y2: 1106,
            x: 2359,
            y: 589
          }
        },
        {
          cubicBezTo: {
            x1: 2883,
            y1: 255,
            x2: 3441,
            y2: 122,
            x: 4048,
            y: 59
          }
        },
        {
          cubicBezTo: {
            x1: 4632,
            y1: 0,
            x2: 5350,
            y2: 0,
            x: 6220,
            y: 0
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 2160,
            y: 9450
          }
        },
        {
          lineTo: {
            x: 2160,
            y: 13770
          }
        },
        {
          cubicBezTo: {
            x1: 2160,
            y1: 14927,
            x2: 2161,
            y2: 15713,
            x: 2201,
            y: 16320
          }
        },
        {
          cubicBezTo: {
            x1: 2239,
            y1: 16911,
            x2: 2309,
            y2: 17215,
            x: 2395,
            y: 17426
          }
        },
        {
          cubicBezTo: {
            x1: 2603,
            y1: 17933,
            x2: 2933,
            y2: 18347,
            x: 3339,
            y: 18606
          }
        },
        {
          cubicBezTo: {
            x1: 3508,
            y1: 18714,
            x2: 3751,
            y2: 18801,
            x: 4224,
            y: 18849
          }
        },
        {
          cubicBezTo: {
            x1: 4710,
            y1: 18899,
            x2: 5338,
            y2: 18900,
            x: 6264,
            y: 18900
          }
        },
        {
          lineTo: {
            x: 15336,
            y: 18900
          }
        },
        {
          cubicBezTo: {
            x1: 16262,
            y1: 18900,
            x2: 16890,
            y2: 18899,
            x: 17376,
            y: 18849
          }
        },
        {
          cubicBezTo: {
            x1: 17849,
            y1: 18801,
            x2: 18092,
            y2: 18714,
            x: 18261,
            y: 18606
          }
        },
        {
          cubicBezTo: {
            x1: 18667,
            y1: 18347,
            x2: 18997,
            y2: 17933,
            x: 19205,
            y: 17426
          }
        },
        {
          cubicBezTo: {
            x1: 19291,
            y1: 17215,
            x2: 19361,
            y2: 16911,
            x: 19399,
            y: 16320
          }
        },
        {
          cubicBezTo: {
            x1: 19439,
            y1: 15713,
            x2: 19440,
            y2: 14927,
            x: 19440,
            y: 13770
          }
        },
        {
          lineTo: {
            x: 19440,
            y: 9450
          }
        },
        {
          lineTo: {
            x: 2160,
            y: 9450
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 19438,
            y: 6750
          }
        },
        {
          cubicBezTo: {
            x1: 19435,
            y1: 6148,
            x2: 19425,
            y2: 5677,
            x: 19399,
            y: 5280
          }
        },
        {
          cubicBezTo: {
            x1: 19361,
            y1: 4689,
            x2: 19291,
            y2: 4385,
            x: 19205,
            y: 4174
          }
        },
        {
          cubicBezTo: {
            x1: 18997,
            y1: 3667,
            x2: 18667,
            y2: 3254,
            x: 18261,
            y: 2994
          }
        },
        {
          cubicBezTo: {
            x1: 18092,
            y1: 2886,
            x2: 17849,
            y2: 2799,
            x: 17376,
            y: 2751
          }
        },
        {
          cubicBezTo: {
            x1: 16890,
            y1: 2701,
            x2: 16262,
            y2: 2700,
            x: 15336,
            y: 2700
          }
        },
        {
          lineTo: {
            x: 6264,
            y: 2700
          }
        },
        {
          cubicBezTo: {
            x1: 5338,
            y1: 2700,
            x2: 4710,
            y2: 2701,
            x: 4224,
            y: 2751
          }
        },
        {
          cubicBezTo: {
            x1: 3751,
            y1: 2799,
            x2: 3508,
            y2: 2886,
            x: 3339,
            y: 2994
          }
        },
        {
          cubicBezTo: {
            x1: 2933,
            y1: 3254,
            x2: 2603,
            y2: 3667,
            x: 2395,
            y: 4174
          }
        },
        {
          cubicBezTo: {
            x1: 2309,
            y1: 4385,
            x2: 2239,
            y2: 4689,
            x: 2201,
            y: 5280
          }
        },
        {
          cubicBezTo: {
            x1: 2175,
            y1: 5677,
            x2: 2165,
            y2: 6148,
            x: 2162,
            y: 6750
          }
        },
        {
          lineTo: {
            x: 19438,
            y: 6750
          }
        },
        {
          close: {}
        },
        {
          moveTo: {
            x: 12960,
            y: 14850
          }
        },
        {
          cubicBezTo: {
            x1: 12960,
            y1: 14105,
            x2: 13444,
            y2: 13500,
            x: 14040,
            y: 13500
          }
        },
        {
          lineTo: {
            x: 16200,
            y: 13500
          }
        },
        {
          cubicBezTo: {
            x1: 16796,
            y1: 13500,
            x2: 17280,
            y2: 14105,
            x: 17280,
            y: 14850
          }
        },
        {
          cubicBezTo: {
            x1: 17280,
            y1: 15595,
            x2: 16796,
            y2: 16200,
            x: 16200,
            y: 16200
          }
        },
        {
          lineTo: {
            x: 14040,
            y: 16200
          }
        },
        {
          cubicBezTo: {
            x1: 13444,
            y1: 16200,
            x2: 12960,
            y2: 15595,
            x: 12960,
            y: 14850
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
    left: 864.21,
    top: 357.67
  },
  width: 35.55,
  height: 28.44
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
