define([
        'backbone',
        'powa/views/WidgetView',
        'powa/models/Grid',
        'backgrid',
        'moment',
        'tpl!powa/templates/grid.html',
        'powa/utils/size',
        'powa/utils/duration',
        'backgrid-filter',
        'backgrid-paginator'],
        function(Backbone, WidgetView, Grid, Backgrid, moment, template, size){

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

    Backgrid.Extension.SizeCell = Backgrid.Cell.extend({
        className: "sizerate",
        formatter: new size.SizeFormatter({suffix: 'ps'})
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

                this.listenTo(this.model, "grid:needrefresh", this.update);
            },

            getColumnDefinitions: function(){
                var columns = [{name: this.model.get("common_group").get("xaxis"),
                                label: this.model.get("x_label"),
                                cell: "string",
                                editable: false}];
                this.model.get("metrics").each(function(metric){
                    var default_cols = {
                        "cell": metric.get("type") || "string"
                    };
                    columns.push($.extend(default_cols, metric.attributes, {
                        name: metric.get("name"),
                        label: metric.get("label"),
                        editable: false,
                    }));
                });
                return columns;
            },

            update: function(){
                this.hideload();
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
