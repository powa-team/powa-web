define([
        'backbone',
        'spin'
    ], function(backbone, Spinner){

    return Backbone.View.extend({

        spinner_opts : {

        },

        showload: function(){
            this.loading = true;
            if(this.spinner === undefined){
                this.spinner = new Spinner(this.spinner_opts);
            }
            this.spinner.spin(this.el);
        },

        fail: function(message){
            this.hideload();
            this.$el.html('<div class="alert-box info">An error occured while loading this widget <br/>' +
                    message + '</div>');
        },

        hideload: function(){
            if(this.spinner){
                this.spinner.stop();
            }
        }


    });
});

