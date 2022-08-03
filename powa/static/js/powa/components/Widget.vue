<template>
  <div>
    <h4>{{ config.title }}</h4>
  </div>
</template>

<script>
export default {
  props: {
    config: {
      type: Object,
      default () {return {}}
    }
  },

  methods: {
    widgetComponent (type) {
      if (type === 'content') {
        // we cannot use <content> reserved HTML tag
        return 'content-cmp';
      }
      return type;
    }
  }
}
</script>
