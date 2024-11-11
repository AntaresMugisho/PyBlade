import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "PyBlade",
  description: "The lightweight and secure template engine for Python web frameworks !",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Documentation', link: '/1-index' }
    ],

    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'What is Pyblade ?', link: '/1-what-is-pyblade' },
          { text: 'Who should use PyBlade ?', link: '/2-who-should-use-pyblade' },
          { text: 'Getting started', link: '/3-getting-started' }
        ]
      },
      {
        text: 'Pyblade : Template engine',
        items: [
          {text: "Comon directives"}
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/antaresmugisho/pyblade' }
    ]
  }
})
