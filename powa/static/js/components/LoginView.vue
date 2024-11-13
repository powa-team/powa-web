<template>
  <v-row class="align-center justify-center" fluid>
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary">
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
            <v-select
              name="server"
              label="Server"
              :items="servers"
              :rules="[rules.required]"
              :model-value="servers.length == 1 ? servers[0] : undefined"
            >
            </v-select>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn class="bg-primary" type="submit">Login</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-col>
  </v-row>
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

const rules = {
  required: (value) => !!value || "Field is required",
};
</script>
