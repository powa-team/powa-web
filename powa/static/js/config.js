require.config({
  baseUrl: "/static/js/",
  paths: {
    almond: "../bower_components/almond/almond",
    backbone: "../bower_components/backbone/backbone",
    d3: "../bower_components/d3/d3",
    foundation: "../bower_components/foundation/js/foundation",
    "foundation-daterangepicker": "../bower_components/foundation-daterangepicker/daterangepicker",
    jquery: "../bower_components/jquery/dist/jquery",
    moment: "../bower_components/moment/moment",
    requirejs: "../bower_components/requirejs/require",
    "requirejs-text": "../bower_components/requirejs-text/text",
    "requirejs-tpl": "../bower_components/requirejs-tpl/tpl",
    tpl: "../bower_components/requirejs-tpl/tpl",
    rickshaw: "../bower_components/rickshaw/rickshaw",
    underscore: "../bower_components/underscore/underscore",
    backgrid: "../bower_components/backgrid/lib/backgrid",
    spin: "../bower_components/spin.js/spin",
    twix: "../bower_components/twix/bin/twix",
    "backgrid-filter": "../bower_components/backgrid-filter/backgrid-filter",
    "backgrid-paginator": "../bower_components/backgrid-paginator/backgrid-paginator",
    "backbone-pageable": "../bower_components/backbone-pageable/lib/backbone-pageable"
  },
  wrapShim: true,
  shim: {
    highlight: {
      exports: "highlight"
    },
    backgrid: {
      deps: [
        "jquery",
        "underscore",
        "backbone"
      ],
      exports: "Backgrid"
    },
    "backgrid-select-all": {
      deps: [
        "backgrid"
      ]
    },
    "backgrid-filter": {
      deps: [
        "backgrid"
      ]
    },
    "backgrid-paginator": {
      deps: [
        "backgrid"
      ]
    }
  },
  packages: [

  ]
});

require(["powa/main"]);
