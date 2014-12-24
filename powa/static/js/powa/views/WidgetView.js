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

        hideload: function(){
            this.spinner.stop();
        }


    });
});

