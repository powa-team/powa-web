define([
        'powa/views/WidgetView',
        'powa/models/Content',
        'highlight',
        'moment',
        'powa/utils/duration'],
function(WidgetView, Content, highlight, moment, duration){
    return WidgetView.extend({
        model: Content,
        typname: "content",

        initialize: function(args){
            this.model = args.model;
            this.listenTo(this.model, "widget:dataload-failed", this.fail);
            this.listenTo(this.model, "widget:needrefresh", this.update);
            this.$el.addClass("content-widget");
        },

        render: function(){
            var self = this;
            this.showload();
            return this;
        },


        update: function(newcontent){
            this.$el.html(newcontent);
            this.$el.find("pre.sql code").each(function(i, block){
                highlight.highlightBlock(block);
            });
            this.$el.find("span.duration").each(function(i, block){
                var date = moment(parseInt($(block).html()));
                $(block).html(date.preciseDiff(moment.unix(0)));
            });
            this.hideload();
            this.trigger("widget:update");
        }

    });

});
