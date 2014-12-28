define([
        'jquery',
        'foundation',
        'backbone',
        'powa/views/WidgetView',
        'powa/models/Grid',
        'backgrid',
        'moment',
        'tpl!powa/templates/grid.html',
        'powa/utils/size',
        'highlight',
        'powa/utils/duration',
        'backgrid-filter',
        'backgrid-paginator'],
        function(jquery, foundation, Backbone, WidgetView, Grid, Backgrid, moment, template, size, highlight){

    var DurationFormatter = {
        fromRaw: function(rawData){
            return moment(parseInt(rawData, 10)).preciseDiff(moment(0));
        }
    };

    Backgrid.Extension.DurationCell = Backgrid.Cell.extend({
        className: "duration",
        formatter: DurationFormatter
    });
    Backgrid.Extension.SizeCell = Backgrid.Cell.extend({
        className: "size",
        formatter: size.SizeFormatter
    });

    Backgrid.Extension.SizerateCell = Backgrid.Cell.extend({
        className: "sizerate",
        formatter: new size.SizeFormatter({suffix: 'ps'})
    });

    Backgrid.Extension.QueryCell= Backgrid.Cell.extend({
        className: "query",
        render: function(){
            this.$el.empty();
            var model = this.model,
                raw_value = model.get(this.column.get("name")),
                value = raw_value.replace(/^\s+/g,"").replace(/\n\s+/, "\n"),
                code_elem = $("<pre>").addClass("has-tip").addClass("tip-top").attr("data-tooltip", "")
                            .html(highlight.highlight("sql", value.substring(0, 35), true).value),
                base = this.$el;
            if(value === undefined){
                return this;
            }
            if(this.column.get("url_attr")){
                base = $("<a>").attr("href", model.get(this.column.get("url_attr")));
                this.$el.append(base);
            }
            base.append(code_elem);
            code_elem.attr("title", "<pre>" + highlight.highlight("sql", raw_value, true).value + "</pre>");
            this.$el.foundation('tooltip', 'reflow');
            this.delegateEvents();
            return this;
        }
    });

    return WidgetView.extend({
            template: template,
            tag: "div",
            model: Grid,

            initialize: function(){
                var self = this;
                this.grid = new Backgrid.Grid({
                    columns: this.getColumnDefinitions(),
                    collection: this.model.get("collection")
                });
                this.filter = new Backgrid.Extension.ClientSideFilter({
                      collection: this.model.get("collection")
                });
                this.paginator = new Backgrid.Extension.Paginator({
                      collection: this.model.get("collection")
                });

                this.listenTo(this.model, "widget:needrefresh", this.update);
            },

            getColumnDefinitions: function(){
                var columns = this.model.get("columns");
                this.model.get("metrics").each(function(metric){
                    columns.push($.extend({}, metric.attributes, {
                        editable: false,
                        cell: metric.get("type")
                    }));
                });
                _.each(columns, function(c){
                    if(c.cell === undefined){
                        c.cell = "string";
                    }
                    if(c.editable === undefined){
                        c.editable = false;
                    }
                });
                return columns;
            },

            update: function(){
                this.hideload();
                this.trigger("widget:update");
            },

            render: function(){
                this.$el.html(this.template(this.model.toJSON()));
                this.$el.find(".grid_container").append(this.grid.render().el);
                this.$el.find(".grid_filter").append(this.filter.render().el);
                this.$el.find(".grid_paginator").append(this.paginator.render().el);
                return this;
            }
        });

});
