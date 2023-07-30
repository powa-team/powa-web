<template>
  <v-container fluid>
    <v-layout align-center justify-center>
      <v-flex xs12 sm8 md4>
        <v-card class="elevation-12">
          <v-toolbar dark color="primary">
            <v-toolbar-title>Login form</v-toolbar-title>
          </v-toolbar>
          <v-form method="post" action="">
            <v-card-text>
              <v-text-field name="user" label="Username"></v-text-field>
              <v-text-field
                name="password"
                label="Password"
                type="password"
              ></v-text-field>
              <v-combobox name="server" label="Server" :items="servers">
              </v-combobox>
            </v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" type="submit">Login</v-btn>
            </v-card-actions>
          </v-form>
        </v-card>
      </v-flex>
    </v-layout>
  </v-container>
</template>

<script setup>
defineProps({
  servers: {
    type: Array,
    default() {
      return [];
    },
  },
});
</script>
