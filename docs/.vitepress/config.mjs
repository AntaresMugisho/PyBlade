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
        text: 'PyBlade : Template engine',
        items: [
          {text: "Displaying Data", link:'/5-displaying-data'},
          {text: "PyBlade Directives", link:'/6-pyblade-directives'},
          {text: "Components", link:'/4-template-engine'},
          {text: "Building Layouts", link:'/4-template-engine'},
          {text: "Forms", link:'/4-template-engine'},
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
