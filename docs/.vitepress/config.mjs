import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "PyBlade",
  description: "The lightweight and secure template engine for Python web frameworks !",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: 'Home', link: '/' },
      { text: 'About', link: '/1-what-is-pyblade'},
      { text: 'Audience', link: '/2-who-should-use-pyblade'},
      { text: 'Documentation', link: '/3-getting-started' }
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
        text: 'PyBlade : Template engine',
        items: [
          {text: "Prelude", link:'/5-prelude'},
          {text: "Displaying Data", link:'/6-displaying-data'},
          {text: "PyBlade Directives", link:'/7-pyblade-directives'},
          {text: "Components",},
          {text: "Building Layouts"},
          {text: "Forms"},
        ]
      },
      {
        text: 'LiveBlade: Interactive UIs',
        items: [
          {}
        ]
      },
      {
        text: 'Outro',
        items: [
          {text: "Future Features", link:'/future-features'},
          {text: "Support and Contribution", link:'/support-and-contribution'},

        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/antaresmugisho/pyblade' }
    ]
  }
})
