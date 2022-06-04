  


<!DOCTYPE html>
<html>
  <head prefix="og: http://ogp.me/ns# fb: http://ogp.me/ns/fb# githubog: http://ogp.me/ns/fb/githubog#">
    <meta charset='utf-8'>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title>configs/vim/colors/rdark_temoto.vim at ec07b43c1882d25e122bd926ed5195a698871cad · temoto/configs</title>
    <link rel="search" type="application/opensearchdescription+xml" href="/opensearch.xml" title="GitHub" />
    <link rel="fluid-icon" href="https://github.com/fluidicon.png" title="GitHub" />
    <link rel="apple-touch-icon-precomposed" sizes="57x57" href="apple-touch-icon-114.png" />
    <link rel="apple-touch-icon-precomposed" sizes="114x114" href="apple-touch-icon-114.png" />
    <link rel="apple-touch-icon-precomposed" sizes="72x72" href="apple-touch-icon-144.png" />
    <link rel="apple-touch-icon-precomposed" sizes="144x144" href="apple-touch-icon-144.png" />

    
    
    <link rel="icon" type="image/x-icon" href="/favicon.png" />

    <meta content="authenticity_token" name="csrf-param" />
<meta content="GjyyGXyl+hatMu1Lx9V/aQcGmT58n1+yEIseep9ULJA=" name="csrf-token" />

    <link href="https://a248.e.akamai.net/assets.github.com/assets/github-6f96eda30ff1556bf501fd7c2915aa0157322687.css" media="screen" rel="stylesheet" type="text/css" />
    <link href="https://a248.e.akamai.net/assets.github.com/assets/github2-c6eeca9bdc855924123b0b9533f2ebe538f56027.css" media="screen" rel="stylesheet" type="text/css" />
    


    <script src="https://a248.e.akamai.net/assets.github.com/assets/frameworks-6f842b2765e7d98b7e93cadc2a364b831cfae37e.js" type="text/javascript"></script>
    <script defer="defer" src="https://a248.e.akamai.net/assets.github.com/assets/github-9a61b3bebbcc2cd7106f4f4dd17f35da2a806090.js" type="text/javascript"></script>
    
    <script defer="defer" src="https://a248.e.akamai.net/assets.github.com/assets/command_bar-2b0f17175d8b1bf5579a2187b49ff62481e9a49d.js" type="text/javascript"></script>

      <link rel='permalink' href='/temoto/configs/blob/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim'>
    <meta property="og:title" content="configs"/>
    <meta property="og:type" content="githubog:gitrepository"/>
    <meta property="og:url" content="https://github.com/temoto/configs"/>
    <meta property="og:image" content="https://a248.e.akamai.net/assets.github.com/images/gravatars/gravatar-user-420.png?1345673561"/>
    <meta property="og:site_name" content="GitHub"/>
    <meta property="og:description" content="my configs are free to read: vim, bash, devtodo. Contribute to configs development by creating an account on GitHub."/>

    <meta name="description" content="my configs are free to read: vim, bash, devtodo. Contribute to configs development by creating an account on GitHub." />
  <link href="https://github.com/temoto/configs/commits/ec07b43c1882d25e122bd926ed5195a698871cad.atom" rel="alternate" title="Recent Commits to configs:ec07b43c1882d25e122bd926ed5195a698871cad" type="application/atom+xml" />

  </head>


  <body class="logged_in page-blob macintosh vis-public env-production ">
    <div id="wrapper">

    
    

      <div id="header" class="true clearfix">
        <div class="container clearfix">
          <a class="site-logo " href="https://github.com/">
            <img alt="GitHub" class="github-logo-4x" height="30" src="https://a248.e.akamai.net/assets.github.com/images/modules/header/logov7@4x.png?1340659530" />
            <img alt="GitHub" class="github-logo-4x-hover" height="30" src="https://a248.e.akamai.net/assets.github.com/images/modules/header/logov7@4x-hover.png?1340659530" />
          </a>

            <a href="/notifications" class="notification-indicator tooltipped downwards" title="You have no unread notifications">
              <span class="mail-status all-read"></span>
            </a>

              
    <div class="topsearch command-bar-activated">
        <form accept-charset="UTF-8" action="/search" class="command_bar_form" id="top_search_form" method="get">
  <a href="/search" class="advanced-search tooltipped downwards command-bar-search" id="advanced_search" title="Advanced Search"><span class="mini-icon mini-icon-advanced-search "></span></a>
  <input type="text" name="q" id="command-bar" placeholder="Search or Type a Command" />
  <span class="mini-icon help tooltipped downwards" title="Show Command Bar Help"></span>
  <input type="hidden" name="type" value="Everything" />
  <input type="hidden" name="repo" value="" />
  <input type="hidden" name="langOverride" value="" />
  <input type="hidden" name="start_value" value="1" />
</form>

      <ul class="top-nav">
          <li class="explore"><a href="https://github.com/explore">Explore</a></li>
          <li><a href="https://gist.github.com">Gist</a></li>
          <li><a href="/blog">Blog</a></li>
        <li><a href="http://help.github.com">Help</a></li>
      </ul>
    </div>


            


  
  <div id="userbox">
    <div id="user">
      <a href="https://github.com/davv3"><img height="20" src="https://secure.gravatar.com/avatar/8fd39a2c4d547eda2be2d9a6f8336dd2?s=140&amp;d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png" width="20" /></a>
      <a href="https://github.com/davv3" class="name">davv3</a>
    </div>
    <ul id="user-links">
      <li>
        <a href="/new" id="new_repo" class="tooltipped downwards" title="Create a New Repo"><span class="mini-icon mini-icon-create"></span></a>
      </li>
      <li>
        <a href="/settings/profile" id="account_settings"
          class="tooltipped downwards"
          title="Account Settings (You have no verified emails)">
          <span class="mini-icon mini-icon-account-settings"></span>
            <span class="setting_warning">!</span>
        </a>
      </li>
      <li>
          <a href="/logout" data-method="post" id="logout" class="tooltipped downwards" title="Sign Out">
            <span class="mini-icon mini-icon-logout"></span>
          </a>
      </li>
    </ul>
  </div>



          
        </div>
      </div>

      <div class="global-notice warn"><div class="global-notice-inner"><h2>You don't have any verified emails.  We recommend <a href="https://github.com/settings/emails">verifying</a> at least one email.</h2><p>Email verification will help our support team help you in case you have any email issues or lose your password.</p></div></div>

      

            <div class="site hfeed" itemscope itemtype="http://schema.org/WebPage">
      <div class="container hentry">
        
        <div class="pagehead repohead instapaper_ignore readability-menu">
        <div class="title-actions-bar">
          


              <ul class="pagehead-actions">

          <li class="subscription">
              <form accept-charset="UTF-8" action="/notifications/subscribe" data-autosubmit="true" data-remote="true" method="post"><div style="margin:0;padding:0;display:inline"><input name="authenticity_token" type="hidden" value="GjyyGXyl+hatMu1Lx9V/aQcGmT58n1+yEIseep9ULJA=" /></div>  <input id="repository_id" name="repository_id" type="hidden" value="69726" />
  <div class="context-menu-container js-menu-container js-context-menu">
    <span class="minibutton switcher bigger js-menu-target">
      <span class="js-context-button">
          <span class="mini-icon mini-icon-watching"></span>Watch
      </span>
    </span>

    <div class="context-pane js-menu-content">
      <a href="javascript:;" class="close js-menu-close"><span class="mini-icon mini-icon-remove-close"></span></a>
      <div class="context-title">Notification status</div>

      <div class="context-body pane-selector">
        <ul class="js-navigation-container">
          <li class="selector-item js-navigation-item js-navigation-target selected">
            <span class="mini-icon mini-icon-confirm"></span>
            <label>
              <input checked="checked" id="do_included" name="do" type="radio" value="included" />
              <h4>Not watching</h4>
              <p>You will only receive notifications when you participate or are mentioned.</p>
            </label>
            <span class="context-button-text js-context-button-text">
              <span class="mini-icon mini-icon-watching"></span>
              Watch
            </span>
          </li>
          <li class="selector-item js-navigation-item js-navigation-target ">
            <span class="mini-icon mini-icon-confirm"></span>
            <label>
              <input id="do_subscribed" name="do" type="radio" value="subscribed" />
              <h4>Watching</h4>
              <p>You will receive all notifications for this repository.</p>
            </label>
            <span class="context-button-text js-context-button-text">
              <span class="mini-icon mini-icon-unwatch"></span>
              Unwatch
            </span>
          </li>
          <li class="selector-item js-navigation-item js-navigation-target ">
            <span class="mini-icon mini-icon-confirm"></span>
            <label>
              <input id="do_ignore" name="do" type="radio" value="ignore" />
              <h4>Ignored</h4>
              <p>You will not receive notifications for this repository.</p>
            </label>
            <span class="context-button-text js-context-button-text">
              <span class="mini-icon mini-icon-mute"></span>
              Stop ignoring
            </span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</form>
          </li>

          <li class="js-toggler-container js-social-container starring-container ">
            <a href="/temoto/configs/unstar" class="minibutton js-toggler-target starred" data-remote="true" data-method="post" rel="nofollow">
              <span class="mini-icon mini-icon-star"></span>Unstar
            </a><a href="/temoto/configs/star" class="minibutton js-toggler-target unstarred" data-remote="true" data-method="post" rel="nofollow">
              <span class="mini-icon mini-icon-star"></span>Star
            </a><a class="social-count js-social-count" href="/temoto/configs/stargazers">4</a>
          </li>

              <li>
                <a href="/temoto/configs/fork_select" class="minibutton js-toggler-target lighter" rel="facebox nofollow"><span class="mini-icon mini-icon-fork"></span>Fork</a><a href="/temoto/configs/network" class="social-count">0</a>
              </li>


    </ul>

          <h1 itemscope itemtype="http://data-vocabulary.org/Breadcrumb" class="entry-title public">
            <span class="repo-label"><span>public</span></span>
            <span class="mega-icon mega-icon-public-repo"></span>
            <span class="author vcard">
              <a href="/temoto" class="url fn" itemprop="url" rel="author">
              <span itemprop="title">temoto</span>
              </a></span> /
            <strong><a href="/temoto/configs" class="js-current-repository">configs</a></strong>
          </h1>
        </div>

          

  <ul class="tabs">
    <li><a href="/temoto/configs/tree/" class="selected" highlight="repo_sourcerepo_downloadsrepo_commitsrepo_tagsrepo_branches">Code</a></li>
    <li><a href="/temoto/configs/network" highlight="repo_network">Network</a></li>
    <li><a href="/temoto/configs/pulls" highlight="repo_pulls">Pull Requests <span class='counter'>0</span></a></li>

      <li><a href="/temoto/configs/issues" highlight="repo_issues">Issues <span class='counter'>0</span></a></li>

      <li><a href="/temoto/configs/wiki" highlight="repo_wiki">Wiki</a></li>


    <li><a href="/temoto/configs/graphs" highlight="repo_graphsrepo_contributors">Graphs</a></li>


  </ul>
  
<div class="frame frame-center tree-finder" style="display:none"
      data-tree-list-url="/temoto/configs/tree-list/ec07b43c1882d25e122bd926ed5195a698871cad"
      data-blob-url-prefix="/temoto/configs/blob/ec07b43c1882d25e122bd926ed5195a698871cad"
    >

  <div class="breadcrumb">
    <span class="bold"><a href="/temoto/configs">configs</a></span> /
    <input class="tree-finder-input js-navigation-enable" type="text" name="query" autocomplete="off" spellcheck="false">
  </div>

    <div class="octotip">
      <p>
        <a href="/temoto/configs/dismiss-tree-finder-help" class="dismiss js-dismiss-tree-list-help" title="Hide this notice forever" rel="nofollow">Dismiss</a>
        <span class="bold">Octotip:</span> You've activated the <em>file finder</em>
        by pressing <span class="kbd">t</span> Start typing to filter the
        file list. Use <span class="kbd badmono">↑</span> and
        <span class="kbd badmono">↓</span> to navigate,
        <span class="kbd">enter</span> to view files.
      </p>
    </div>

  <table class="tree-browser" cellpadding="0" cellspacing="0">
    <tr class="js-header"><th>&nbsp;</th><th>name</th></tr>
    <tr class="js-no-results no-results" style="display: none">
      <th colspan="2">No matching files</th>
    </tr>
    <tbody class="js-results-list js-navigation-container">
    </tbody>
  </table>
</div>

<div id="jump-to-line" style="display:none">
  <h2>Jump to Line</h2>
  <form accept-charset="UTF-8">
    <input class="textfield" type="text">
    <div class="full-button">
      <button type="submit" class="classy">
        Go
      </button>
    </div>
  </form>
</div>


<div class="tabnav">

  <span class="tabnav-right">
    <ul class="tabnav-tabs">
      <li><a href="/temoto/configs/tags" class="tabnav-tab" highlight="repo_tags">Tags <span class="counter blank">0</span></a></li>
      <li><a href="/temoto/configs/downloads" class="tabnav-tab" highlight="repo_downloads">Downloads <span class="counter blank">0</span></a></li>
    </ul>
    
  </span>

  <div class="tabnav-widget scope">

    <div class="context-menu-container js-menu-container js-context-menu">
      <a href="#"
         class="minibutton bigger switcher js-menu-target js-commitish-button btn-tree repo-tree"
         data-hotkey="w"
         data-master-branch="master"
         data-ref="">
         <span><em class="mini-icon mini-icon-tree"></em><i>tree:</i> ec07b43c18</span>
      </a>

      <div class="context-pane commitish-context js-menu-content">
        <a href="javascript:;" class="close js-menu-close"><span class="mini-icon mini-icon-remove-close"></span></a>
        <div class="context-title">Switch branches/tags</div>
        <div class="context-body pane-selector commitish-selector js-navigation-container">
          <div class="filterbar">
            <input type="text" id="context-commitish-filter-field" class="js-navigation-enable" placeholder="Filter branches/tags" data-filterable />
            <ul class="tabs">
              <li><a href="#" data-filter="branches" class="selected">Branches</a></li>
              <li><a href="#" data-filter="tags">Tags</a></li>
            </ul>
          </div>

          <div class="js-filter-tab js-filter-branches" data-filterable-for="context-commitish-filter-field" data-filterable-type=substring>
            <div class="no-results js-not-filterable">Nothing to show</div>
              <div class="commitish-item branch-commitish selector-item js-navigation-item js-navigation-target ">
                <span class="mini-icon mini-icon-confirm"></span>
                <h4>
                    <a href="/temoto/configs/blob/master/vim/colors/rdark_temoto.vim" class="js-navigation-open" data-name="master" rel="nofollow">master</a>
                </h4>
              </div>
          </div>

          <div class="js-filter-tab js-filter-tags" style="display:none" data-filterable-for="context-commitish-filter-field" data-filterable-type=substring>
            <div class="no-results js-not-filterable">Nothing to show</div>
          </div>
        </div>
      </div><!-- /.commitish-context-context -->
    </div>
  </div> <!-- /.scope -->

  <ul class="tabnav-tabs">
    <li><a href="/temoto/configs/tree/" class="selected tabnav-tab" highlight="repo_source">Files</a></li>
    <li><a href="/temoto/configs/commits/" class="tabnav-tab" highlight="repo_commits">Commits</a></li>
    <li><a href="/temoto/configs/branches" class="tabnav-tab" highlight="repo_branches" rel="nofollow">Branches <span class="counter ">1</span></a></li>
  </ul>

</div>

  
  
  


          

        </div><!-- /.repohead -->

        <div id="js-repo-pjax-container" data-pjax-container>
          


<!-- blob contrib key: blob_contributors:v21:1d28701885de943aa622e987e846b62a -->
<!-- blob contrib frag key: views10/v8/blob_contributors:v21:1d28701885de943aa622e987e846b62a -->

<!-- block_view_fragment_key: views10/v8/blob:v21:d6398bb6215d1cec9f963e1598b2dae8 -->
  <div id="slider">

    <div class="breadcrumb" data-path="vim/colors/rdark_temoto.vim/">
      <b itemscope="" itemtype="http://data-vocabulary.org/Breadcrumb"><a href="/temoto/configs/tree/ec07b43c1882d25e122bd926ed5195a698871cad" class="js-rewrite-sha" itemprop="url"><span itemprop="title">configs</span></a></b> / <span itemscope="" itemtype="http://data-vocabulary.org/Breadcrumb"><a href="/temoto/configs/tree/ec07b43c1882d25e122bd926ed5195a698871cad/vim" class="js-rewrite-sha" itemscope="url"><span itemprop="title">vim</span></a></span> / <span itemscope="" itemtype="http://data-vocabulary.org/Breadcrumb"><a href="/temoto/configs/tree/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors" class="js-rewrite-sha" itemscope="url"><span itemprop="title">colors</span></a></span> / <strong class="final-path">rdark_temoto.vim</strong> <span class="js-clippy mini-icon mini-icon-clippy " data-clipboard-text="vim/colors/rdark_temoto.vim" data-copied-hint="copied!" data-copy-hint="copy to clipboard"></span>
    </div>

      
  <div class="commit file-history-tease js-blob-contributors-content" data-path="vim/colors/rdark_temoto.vim/">
    <img class="main-avatar" height="24" src="https://secure.gravatar.com/avatar/8472b094c8d96dead7e05f0ec2b61b4d?s=140&amp;d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-user-420.png" width="24" />
    <span class="author">temoto</span>
    <time class="js-relative-date" datetime="2008-10-30T07:28:15-07:00" title="2008-10-30 07:28:15">October 30, 2008</time>
    <div class="commit-title">
        <a href="/temoto/configs/commit/2925fb78d150a535263e8f2998fed0ec345c018c" class="message">added vim configs</a>
    </div>

    <div class="participation">
      <p class="quickstat"><a href="#blob_contributors_box" rel="facebox"><strong>0</strong> contributors</a></p>
      
    </div>
    <div id="blob_contributors_box" style="display:none">
      <h2>Users on GitHub who have contributed to this file</h2>
      <ul class="facebox-user-list">
      </ul>
    </div>
  </div>


    <div class="frames">
      <div class="frame frame-center" data-path="vim/colors/rdark_temoto.vim/" data-permalink-url="/temoto/configs/blob/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim" data-title="configs/vim/colors/rdark_temoto.vim at ec07b43c1882d25e122bd926ed5195a698871cad · temoto/configs · GitHub" data-type="blob">

        <div id="files" class="bubble">
          <div class="file">
            <div class="meta">
              <div class="info">
                <span class="icon"><b class="mini-icon mini-icon-text-file"></b></span>
                <span class="mode" title="File Mode">executable file</span>
                  <span>160 lines (139 sloc)</span>
                <span>3.965 kb</span>
              </div>
              <ul class="button-group actions">
                  <li>
                    <a class="grouped-button file-edit-link minibutton bigger lighter js-rewrite-sha" href="/temoto/configs/edit/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim" data-method="post" rel="nofollow" data-hotkey="e">Edit</a>
                  </li>
                <li>
                  <a href="/temoto/configs/raw/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim" class="minibutton grouped-button bigger lighter" id="raw-url">Raw</a>
                </li>
                  <li>
                    <a href="/temoto/configs/blame/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim" class="minibutton grouped-button bigger lighter">Blame</a>
                  </li>
                <li>
                  <a href="/temoto/configs/commits/ec07b43c1882d25e122bd926ed5195a698871cad/vim/colors/rdark_temoto.vim" class="minibutton grouped-button bigger lighter" rel="nofollow">History</a>
                </li>
              </ul>
            </div>
              <div class="data type-viml">
      <table cellpadding="0" cellspacing="0" class="lines">
        <tr>
          <td>
            <pre class="line_numbers"><span id="L1" rel="#L1">1</span>
<span id="L2" rel="#L2">2</span>
<span id="L3" rel="#L3">3</span>
<span id="L4" rel="#L4">4</span>
<span id="L5" rel="#L5">5</span>
<span id="L6" rel="#L6">6</span>
<span id="L7" rel="#L7">7</span>
<span id="L8" rel="#L8">8</span>
<span id="L9" rel="#L9">9</span>
<span id="L10" rel="#L10">10</span>
<span id="L11" rel="#L11">11</span>
<span id="L12" rel="#L12">12</span>
<span id="L13" rel="#L13">13</span>
<span id="L14" rel="#L14">14</span>
<span id="L15" rel="#L15">15</span>
<span id="L16" rel="#L16">16</span>
<span id="L17" rel="#L17">17</span>
<span id="L18" rel="#L18">18</span>
<span id="L19" rel="#L19">19</span>
<span id="L20" rel="#L20">20</span>
<span id="L21" rel="#L21">21</span>
<span id="L22" rel="#L22">22</span>
<span id="L23" rel="#L23">23</span>
<span id="L24" rel="#L24">24</span>
<span id="L25" rel="#L25">25</span>
<span id="L26" rel="#L26">26</span>
<span id="L27" rel="#L27">27</span>
<span id="L28" rel="#L28">28</span>
<span id="L29" rel="#L29">29</span>
<span id="L30" rel="#L30">30</span>
<span id="L31" rel="#L31">31</span>
<span id="L32" rel="#L32">32</span>
<span id="L33" rel="#L33">33</span>
<span id="L34" rel="#L34">34</span>
<span id="L35" rel="#L35">35</span>
<span id="L36" rel="#L36">36</span>
<span id="L37" rel="#L37">37</span>
<span id="L38" rel="#L38">38</span>
<span id="L39" rel="#L39">39</span>
<span id="L40" rel="#L40">40</span>
<span id="L41" rel="#L41">41</span>
<span id="L42" rel="#L42">42</span>
<span id="L43" rel="#L43">43</span>
<span id="L44" rel="#L44">44</span>
<span id="L45" rel="#L45">45</span>
<span id="L46" rel="#L46">46</span>
<span id="L47" rel="#L47">47</span>
<span id="L48" rel="#L48">48</span>
<span id="L49" rel="#L49">49</span>
<span id="L50" rel="#L50">50</span>
<span id="L51" rel="#L51">51</span>
<span id="L52" rel="#L52">52</span>
<span id="L53" rel="#L53">53</span>
<span id="L54" rel="#L54">54</span>
<span id="L55" rel="#L55">55</span>
<span id="L56" rel="#L56">56</span>
<span id="L57" rel="#L57">57</span>
<span id="L58" rel="#L58">58</span>
<span id="L59" rel="#L59">59</span>
<span id="L60" rel="#L60">60</span>
<span id="L61" rel="#L61">61</span>
<span id="L62" rel="#L62">62</span>
<span id="L63" rel="#L63">63</span>
<span id="L64" rel="#L64">64</span>
<span id="L65" rel="#L65">65</span>
<span id="L66" rel="#L66">66</span>
<span id="L67" rel="#L67">67</span>
<span id="L68" rel="#L68">68</span>
<span id="L69" rel="#L69">69</span>
<span id="L70" rel="#L70">70</span>
<span id="L71" rel="#L71">71</span>
<span id="L72" rel="#L72">72</span>
<span id="L73" rel="#L73">73</span>
<span id="L74" rel="#L74">74</span>
<span id="L75" rel="#L75">75</span>
<span id="L76" rel="#L76">76</span>
<span id="L77" rel="#L77">77</span>
<span id="L78" rel="#L78">78</span>
<span id="L79" rel="#L79">79</span>
<span id="L80" rel="#L80">80</span>
<span id="L81" rel="#L81">81</span>
<span id="L82" rel="#L82">82</span>
<span id="L83" rel="#L83">83</span>
<span id="L84" rel="#L84">84</span>
<span id="L85" rel="#L85">85</span>
<span id="L86" rel="#L86">86</span>
<span id="L87" rel="#L87">87</span>
<span id="L88" rel="#L88">88</span>
<span id="L89" rel="#L89">89</span>
<span id="L90" rel="#L90">90</span>
<span id="L91" rel="#L91">91</span>
<span id="L92" rel="#L92">92</span>
<span id="L93" rel="#L93">93</span>
<span id="L94" rel="#L94">94</span>
<span id="L95" rel="#L95">95</span>
<span id="L96" rel="#L96">96</span>
<span id="L97" rel="#L97">97</span>
<span id="L98" rel="#L98">98</span>
<span id="L99" rel="#L99">99</span>
<span id="L100" rel="#L100">100</span>
<span id="L101" rel="#L101">101</span>
<span id="L102" rel="#L102">102</span>
<span id="L103" rel="#L103">103</span>
<span id="L104" rel="#L104">104</span>
<span id="L105" rel="#L105">105</span>
<span id="L106" rel="#L106">106</span>
<span id="L107" rel="#L107">107</span>
<span id="L108" rel="#L108">108</span>
<span id="L109" rel="#L109">109</span>
<span id="L110" rel="#L110">110</span>
<span id="L111" rel="#L111">111</span>
<span id="L112" rel="#L112">112</span>
<span id="L113" rel="#L113">113</span>
<span id="L114" rel="#L114">114</span>
<span id="L115" rel="#L115">115</span>
<span id="L116" rel="#L116">116</span>
<span id="L117" rel="#L117">117</span>
<span id="L118" rel="#L118">118</span>
<span id="L119" rel="#L119">119</span>
<span id="L120" rel="#L120">120</span>
<span id="L121" rel="#L121">121</span>
<span id="L122" rel="#L122">122</span>
<span id="L123" rel="#L123">123</span>
<span id="L124" rel="#L124">124</span>
<span id="L125" rel="#L125">125</span>
<span id="L126" rel="#L126">126</span>
<span id="L127" rel="#L127">127</span>
<span id="L128" rel="#L128">128</span>
<span id="L129" rel="#L129">129</span>
<span id="L130" rel="#L130">130</span>
<span id="L131" rel="#L131">131</span>
<span id="L132" rel="#L132">132</span>
<span id="L133" rel="#L133">133</span>
<span id="L134" rel="#L134">134</span>
<span id="L135" rel="#L135">135</span>
<span id="L136" rel="#L136">136</span>
<span id="L137" rel="#L137">137</span>
<span id="L138" rel="#L138">138</span>
<span id="L139" rel="#L139">139</span>
<span id="L140" rel="#L140">140</span>
<span id="L141" rel="#L141">141</span>
<span id="L142" rel="#L142">142</span>
<span id="L143" rel="#L143">143</span>
<span id="L144" rel="#L144">144</span>
<span id="L145" rel="#L145">145</span>
<span id="L146" rel="#L146">146</span>
<span id="L147" rel="#L147">147</span>
<span id="L148" rel="#L148">148</span>
<span id="L149" rel="#L149">149</span>
<span id="L150" rel="#L150">150</span>
<span id="L151" rel="#L151">151</span>
<span id="L152" rel="#L152">152</span>
<span id="L153" rel="#L153">153</span>
<span id="L154" rel="#L154">154</span>
<span id="L155" rel="#L155">155</span>
<span id="L156" rel="#L156">156</span>
<span id="L157" rel="#L157">157</span>
<span id="L158" rel="#L158">158</span>
<span id="L159" rel="#L159">159</span>
</pre>
          </td>
          <td width="100%">
                <div class="highlight"><pre><div class='line' id='LC1'><span class="c">&quot; Vim color file</span></div><div class='line' id='LC2'><span class="c">&quot; Maintaner: Radu Dineiu &lt;radu.dineiu@gmail.com&gt;</span></div><div class='line' id='LC3'><span class="c">&quot; URL: http://ld.yi.org/vim/rdark/</span></div><div class='line' id='LC4'><span class="c">&quot; Last Change: 2007 Jun 23</span></div><div class='line' id='LC5'><span class="c">&quot; Version: 0.6</span></div><div class='line' id='LC6'><span class="c">&quot;</span></div><div class='line' id='LC7'><span class="c">&quot; Features:</span></div><div class='line' id='LC8'><span class="c">&quot;   - let rdark_current_line = 1 if you want to highlight the current line</span></div><div class='line' id='LC9'><span class="c">&quot;</span></div><div class='line' id='LC10'><span class="c">&quot; Changelog:</span></div><div class='line' id='LC11'><span class="c">&quot;   0.5 - fixed the Pmenu colors</span></div><div class='line' id='LC12'><span class="c">&quot;   0.6 - added SignColumn colors</span></div><div class='line' id='LC13'><br/></div><div class='line' id='LC14'><span class="k">set</span> <span class="nb">background</span><span class="p">=</span><span class="nb">dark</span></div><div class='line' id='LC15'><br/></div><div class='line' id='LC16'><span class="k">hi</span> clear</div><div class='line' id='LC17'><span class="k">if</span> exists<span class="p">(</span><span class="s2">&quot;syntax_on&quot;</span><span class="p">)</span></div><div class='line' id='LC18'>	<span class="nb">syntax</span> reset</div><div class='line' id='LC19'><span class="k">endif</span></div><div class='line' id='LC20'><br/></div><div class='line' id='LC21'><span class="k">let</span> colors_name <span class="p">=</span> <span class="s2">&quot;rdark_temoto&quot;</span></div><div class='line' id='LC22'><br/></div><div class='line' id='LC23'><span class="c">&quot; Current Line</span></div><div class='line' id='LC24'><span class="k">if</span> exists<span class="p">(</span><span class="s1">&#39;rdark_current_line&#39;</span><span class="p">)</span> &amp;&amp; rdark_current_line <span class="p">==</span> <span class="m">1</span></div><div class='line' id='LC25'>	<span class="k">set</span> <span class="nb">cursorline</span></div><div class='line' id='LC26'>	<span class="k">hi</span> CursorLine guibg<span class="p">=</span><span class="mh">#191f21</span></div><div class='line' id='LC27'><span class="k">endif</span></div><div class='line' id='LC28'><br/></div><div class='line' id='LC29'><span class="c">&quot; Default Colors</span></div><div class='line' id='LC30'><span class="k">hi</span> Normal guifg<span class="p">=</span><span class="mh">#daddd6</span> guibg<span class="p">=</span><span class="mh">#1e2426</span></div><div class='line' id='LC31'><span class="k">hi</span> NonText guifg<span class="p">=</span><span class="mh">#2c3032</span> guibg<span class="p">=</span><span class="mh">#2c3032</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC32'><span class="k">hi</span> Cursor guibg<span class="p">=</span><span class="mh">#babdb6</span></div><div class='line' id='LC33'><span class="k">hi</span> ICursor guibg<span class="p">=</span><span class="mh">#babdb6</span></div><div class='line' id='LC34'><br/></div><div class='line' id='LC35'><span class="c">&quot; Search</span></div><div class='line' id='LC36'><span class="k">hi</span> Search guifg<span class="p">=</span><span class="mh">#2e3436</span> guibg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC37'><span class="k">hi</span> IncSearch guibg<span class="p">=</span><span class="mh">#2e3436</span> guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC38'><br/></div><div class='line' id='LC39'><span class="c">&quot; Window Elements</span></div><div class='line' id='LC40'><span class="k">hi</span> StatusLine guifg<span class="p">=</span><span class="mh">#2e3436</span> guibg<span class="p">=</span><span class="mh">#babdb6</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC41'><span class="k">hi</span> StatusLineNC guifg<span class="p">=</span><span class="mh">#2e3436</span> guibg<span class="p">=</span><span class="mh">#888a85</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC42'><span class="k">hi</span> VertSplit guifg<span class="p">=</span><span class="mh">#555753</span> guibg<span class="p">=</span><span class="mh">#888a85</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC43'><span class="k">hi</span> Visual guibg<span class="p">=</span><span class="mh">#696969</span></div><div class='line' id='LC44'><span class="k">hi</span> MoreMsg guifg<span class="p">=</span><span class="mh">#729fcf</span></div><div class='line' id='LC45'><span class="k">hi</span> Question guifg<span class="p">=</span><span class="mh">#8ae234</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC46'><span class="k">hi</span> WildMenu guifg<span class="p">=</span><span class="mh">#000000</span> guibg<span class="p">=</span><span class="mh">#6ac214</span></div><div class='line' id='LC47'><span class="k">hi</span> LineNr guifg<span class="p">=</span><span class="mh">#5f6b6d</span> guibg<span class="p">=</span><span class="mh">#000000</span></div><div class='line' id='LC48'><span class="k">hi</span> SignColumn guibg<span class="p">=</span><span class="mh">#1e2426</span></div><div class='line' id='LC49'><br/></div><div class='line' id='LC50'><span class="c">&quot; Pmenu</span></div><div class='line' id='LC51'><span class="k">hi</span> Pmenu guibg<span class="p">=</span><span class="mh">#2e3436</span> guifg<span class="p">=</span><span class="mh">#eeeeec</span></div><div class='line' id='LC52'><span class="k">hi</span> PmenuSel guibg<span class="p">=</span><span class="mh">#ffffff</span> guifg<span class="p">=</span><span class="mh">#1e2426</span></div><div class='line' id='LC53'><span class="k">hi</span> PmenuSbar guibg<span class="p">=</span><span class="mh">#555753</span></div><div class='line' id='LC54'><span class="k">hi</span> PmenuThumb guifg<span class="p">=</span><span class="mh">#ffffff</span></div><div class='line' id='LC55'><br/></div><div class='line' id='LC56'><span class="c">&quot; Diff</span></div><div class='line' id='LC57'><span class="k">hi</span> DiffDelete guifg<span class="p">=</span><span class="mh">#2e3436</span> guibg<span class="p">=</span><span class="mh">#0e1416</span></div><div class='line' id='LC58'><span class="k">hi</span> DiffAdd guibg<span class="p">=</span><span class="mh">#1f2b2d</span></div><div class='line' id='LC59'><span class="k">hi</span> DiffChange guibg<span class="p">=</span><span class="mh">#2e3436</span></div><div class='line' id='LC60'><span class="k">hi</span> DiffText guibg<span class="p">=</span><span class="mh">#000000</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC61'><br/></div><div class='line' id='LC62'><span class="c">&quot; Folds</span></div><div class='line' id='LC63'><span class="k">hi</span> Folded guifg<span class="p">=</span><span class="mh">#d3d7cf</span> guibg<span class="p">=</span><span class="mh">#204a87</span></div><div class='line' id='LC64'><span class="k">hi</span> FoldColumn guifg<span class="p">=</span><span class="mh">#3465a4</span> guibg<span class="p">=</span><span class="mh">#000000</span></div><div class='line' id='LC65'><br/></div><div class='line' id='LC66'><span class="c">&quot; Specials</span></div><div class='line' id='LC67'><span class="k">hi</span> Title guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC68'><span class="k">hi</span> Todo guifg<span class="p">=</span><span class="mh">#fcaf3e</span> guibg<span class="p">=</span><span class="nb">bg</span> <span class="k">gui</span><span class="p">=</span><span class="nb">bold</span></div><div class='line' id='LC69'><span class="k">hi</span> SpecialKey guifg<span class="p">=</span><span class="mh">#701919</span> guibg<span class="p">=</span><span class="mh">#101c1e</span> <span class="k">gui</span><span class="p">=</span><span class="nb">bold</span></div><div class='line' id='LC70'><br/></div><div class='line' id='LC71'><span class="c">&quot; Tabs</span></div><div class='line' id='LC72'><span class="k">hi</span> TabLine guibg<span class="p">=</span><span class="mh">#0a1012</span> guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC73'><span class="k">hi</span> TabLineFill guifg<span class="p">=</span><span class="mh">#0a1012</span></div><div class='line' id='LC74'><span class="k">hi</span> TabLineSel guibg<span class="p">=</span><span class="mh">#555753</span> guifg<span class="p">=</span><span class="mh">#eeeeec</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC75'><br/></div><div class='line' id='LC76'><span class="c">&quot; Matches</span></div><div class='line' id='LC77'><span class="k">hi</span> MatchParen guifg<span class="p">=</span><span class="mh">#2e3436</span> guibg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC78'><br/></div><div class='line' id='LC79'><span class="c">&quot; Tree</span></div><div class='line' id='LC80'><span class="k">hi</span> Directory guifg<span class="p">=</span><span class="mh">#628fbf</span> <span class="k">gui</span><span class="p">=</span><span class="nb">bold</span></div><div class='line' id='LC81'><br/></div><div class='line' id='LC82'><span class="c">&quot; Syntax</span></div><div class='line' id='LC83'><span class="k">hi</span> Comment guifg<span class="p">=</span><span class="mh">#858683</span></div><div class='line' id='LC84'><span class="k">hi</span> Constant guifg<span class="p">=</span><span class="mh">#8ae234</span> guibg<span class="p">=</span><span class="mh">#000000</span></div><div class='line' id='LC85'><span class="k">hi</span> Number guifg<span class="p">=</span><span class="mh">#8ae234</span></div><div class='line' id='LC86'><span class="k">hi</span> Statement guifg<span class="p">=</span><span class="mh">#729fcf</span> <span class="k">gui</span><span class="p">=</span><span class="nb">bold</span></div><div class='line' id='LC87'><span class="k">hi</span> Identifier guifg<span class="p">=</span><span class="mh">#ffffff</span></div><div class='line' id='LC88'><span class="k">hi</span> PreProc guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC89'><span class="k">hi</span> Function guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC90'><span class="k">hi</span> Type guifg<span class="p">=</span><span class="mh">#e3e7df</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC91'><span class="k">hi</span> Keyword guifg<span class="p">=</span><span class="mh">#eeeeec</span></div><div class='line' id='LC92'><span class="k">hi</span> Special guifg<span class="p">=</span><span class="mh">#dc8f1e</span> guibg<span class="p">=</span><span class="mh">#000000</span></div><div class='line' id='LC93'><span class="k">hi</span> <span class="k">Error</span> guifg<span class="p">=</span><span class="mh">#eeeeec</span> guibg<span class="p">=</span><span class="mh">#cc0000</span></div><div class='line' id='LC94'><br/></div><div class='line' id='LC95'><span class="c">&quot; PHP</span></div><div class='line' id='LC96'><span class="k">hi</span> phpRegionDelimiter guifg<span class="p">=</span><span class="mh">#ad7fa8</span></div><div class='line' id='LC97'><span class="k">hi</span> phpPropertySelector guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC98'><span class="k">hi</span> phpPropertySelectorInString guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC99'><span class="k">hi</span> phpOperator guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC100'><span class="k">hi</span> phpArrayPair guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC101'><span class="k">hi</span> phpAssignByRef guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC102'><span class="k">hi</span> phpRelation guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC103'><span class="k">hi</span> phpMemberSelector guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC104'><span class="k">hi</span> phpUnknownSelector guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC105'><span class="k">hi</span> phpVarSelector guifg<span class="p">=</span><span class="mh">#babdb6</span></div><div class='line' id='LC106'><span class="k">hi</span> phpSemicolon guifg<span class="p">=</span><span class="mh">#888a85</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC107'><span class="k">hi</span> phpFunctions guifg<span class="p">=</span><span class="mh">#d3d7cf</span></div><div class='line' id='LC108'><span class="k">hi</span> phpParent guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC109'><br/></div><div class='line' id='LC110'><span class="c">&quot; JavaScript</span></div><div class='line' id='LC111'><span class="k">hi</span> javaScriptBraces guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC112'><span class="k">hi</span> javaScriptOperator guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC113'><br/></div><div class='line' id='LC114'><span class="c">&quot; HTML</span></div><div class='line' id='LC115'><span class="k">hi</span> htmlTag guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC116'><span class="k">hi</span> htmlEndTag guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC117'><span class="k">hi</span> htmlTagName guifg<span class="p">=</span><span class="mh">#babdb6</span></div><div class='line' id='LC118'><span class="k">hi</span> htmlSpecialTagName guifg<span class="p">=</span><span class="mh">#babdb6</span></div><div class='line' id='LC119'><span class="k">hi</span> htmlArg guifg<span class="p">=</span><span class="mh">#d3d7cf</span></div><div class='line' id='LC120'><span class="k">hi</span> htmlTitle guifg<span class="p">=</span><span class="mh">#8ae234</span> <span class="k">gui</span><span class="p">=</span>none</div><div class='line' id='LC121'><span class="k">hi</span> link htmlH1 htmlTitle</div><div class='line' id='LC122'><span class="k">hi</span> link htmlH2 htmlH1</div><div class='line' id='LC123'><span class="k">hi</span> link htmlH3 htmlH1</div><div class='line' id='LC124'><span class="k">hi</span> link htmlH4 htmlH1</div><div class='line' id='LC125'><span class="k">hi</span> link htmlH5 htmlH1</div><div class='line' id='LC126'><span class="k">hi</span> link htmlH6 htmlH1</div><div class='line' id='LC127'><br/></div><div class='line' id='LC128'><span class="c">&quot; XML</span></div><div class='line' id='LC129'><span class="k">hi</span> link xmlTag htmlTag</div><div class='line' id='LC130'><span class="k">hi</span> link xmlEndTag htmlEndTag</div><div class='line' id='LC131'><span class="k">hi</span> link xmlAttrib htmlArg</div><div class='line' id='LC132'><br/></div><div class='line' id='LC133'><span class="c">&quot; CSS</span></div><div class='line' id='LC134'><span class="k">hi</span> cssSelectorOp guifg<span class="p">=</span><span class="mh">#eeeeec</span></div><div class='line' id='LC135'><span class="k">hi</span> link cssSelectorOp2 cssSelectorOp</div><div class='line' id='LC136'><span class="k">hi</span> cssUIProp guifg<span class="p">=</span><span class="mh">#d3d7cf</span></div><div class='line' id='LC137'><span class="k">hi</span> link cssPagingProp cssUIProp</div><div class='line' id='LC138'><span class="k">hi</span> link cssGeneratedContentProp cssUIProp</div><div class='line' id='LC139'><span class="k">hi</span> link cssRenderProp cssUIProp</div><div class='line' id='LC140'><span class="k">hi</span> link cssBoxProp cssUIProp</div><div class='line' id='LC141'><span class="k">hi</span> link cssTextProp cssUIProp</div><div class='line' id='LC142'><span class="k">hi</span> link cssColorProp cssUIProp</div><div class='line' id='LC143'><span class="k">hi</span> link cssFontProp cssUIProp</div><div class='line' id='LC144'><span class="k">hi</span> cssPseudoClassId guifg<span class="p">=</span><span class="mh">#eeeeec</span></div><div class='line' id='LC145'><span class="k">hi</span> cssBraces guifg<span class="p">=</span><span class="mh">#888a85</span></div><div class='line' id='LC146'><span class="k">hi</span> cssIdentifier guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC147'><span class="k">hi</span> cssTagName guifg<span class="p">=</span><span class="mh">#fcaf3e</span></div><div class='line' id='LC148'><span class="k">hi</span> link cssInclude Function</div><div class='line' id='LC149'><span class="k">hi</span> link cssCommonAttr Constant</div><div class='line' id='LC150'><span class="k">hi</span> link cssUIAttr Constant</div><div class='line' id='LC151'><span class="k">hi</span> link cssTableAttr Constant</div><div class='line' id='LC152'><span class="k">hi</span> link cssPagingAttr Constant</div><div class='line' id='LC153'><span class="k">hi</span> link cssGeneratedContentAttr Constant</div><div class='line' id='LC154'><span class="k">hi</span> link cssAuralAttr Constant</div><div class='line' id='LC155'><span class="k">hi</span> link cssRenderAttr Constant</div><div class='line' id='LC156'><span class="k">hi</span> link cssBoxAttr Constant</div><div class='line' id='LC157'><span class="k">hi</span> link cssTextAttr Constant</div><div class='line' id='LC158'><span class="k">hi</span> link cssColorAttr Constant</div><div class='line' id='LC159'><span class="k">hi</span> link cssFontAttr Constant</div></pre></div>
          </td>
        </tr>
      </table>
  </div>

          </div>
        </div>
      </div>
    </div>

  </div>

<div class="frame frame-loading large-loading-area" style="display:none;" data-tree-list-url="/temoto/configs/tree-list/ec07b43c1882d25e122bd926ed5195a698871cad" data-blob-url-prefix="/temoto/configs/blob/ec07b43c1882d25e122bd926ed5195a698871cad">
  <img src="https://a248.e.akamai.net/assets.github.com/images/spinners/octocat-spinner-128.gif?1347543525" height="64" width="64">
</div>

        </div>
      </div>
      <div class="context-overlay"></div>
    </div>

      <div id="footer-push"></div><!-- hack for sticky footer -->
    </div><!-- end of wrapper - hack for sticky footer -->

      <!-- footer -->
      <div id="footer" >
        
  <div class="upper_footer">
     <div class="container clearfix">

       <!--[if IE]><h4 id="blacktocat_ie">GitHub Links</h4><![endif]-->
       <![if !IE]><h4 id="blacktocat">GitHub Links</h4><![endif]>

       <ul class="footer_nav">
         <h4>GitHub</h4>
         <li><a href="https://github.com/about">About</a></li>
         <li><a href="https://github.com/blog">Blog</a></li>
         <li><a href="https://github.com/features">Features</a></li>
         <li><a href="https://github.com/contact">Contact &amp; Support</a></li>
         <li><a href="https://github.com/training">Training</a></li>
         <li><a href="http://enterprise.github.com/">GitHub Enterprise</a></li>
         <li><a href="http://status.github.com/">Site Status</a></li>
       </ul>

       <ul class="footer_nav">
         <h4>Clients</h4>
         <li><a href="http://mac.github.com/">GitHub for Mac</a></li>
         <li><a href="http://windows.github.com/">GitHub for Windows</a></li>
         <li><a href="http://eclipse.github.com/">GitHub for Eclipse</a></li>
         <li><a href="http://mobile.github.com/">GitHub Mobile Apps</a></li>
       </ul>

       <ul class="footer_nav">
         <h4>Tools</h4>
         <li><a href="http://get.gaug.es/">Gauges: Web analytics</a></li>
         <li><a href="http://speakerdeck.com">Speaker Deck: Presentations</a></li>
         <li><a href="https://gist.github.com">Gist: Code snippets</a></li>

         <h4 class="second">Extras</h4>
         <li><a href="http://jobs.github.com/">Job Board</a></li>
         <li><a href="http://shop.github.com/">GitHub Shop</a></li>
         <li><a href="http://octodex.github.com/">The Octodex</a></li>
       </ul>

       <ul class="footer_nav">
         <h4>Documentation</h4>
         <li><a href="http://help.github.com/">GitHub Help</a></li>
         <li><a href="http://developer.github.com/">Developer API</a></li>
         <li><a href="http://github.github.com/github-flavored-markdown/">GitHub Flavored Markdown</a></li>
         <li><a href="http://pages.github.com/">GitHub Pages</a></li>
       </ul>

     </div><!-- /.site -->
  </div><!-- /.upper_footer -->

<div class="lower_footer">
  <div class="container clearfix">
    <!--[if IE]><div id="legal_ie"><![endif]-->
    <![if !IE]><div id="legal"><![endif]>
      <ul>
          <li><a href="https://github.com/site/terms">Terms of Service</a></li>
          <li><a href="https://github.com/site/privacy">Privacy</a></li>
          <li><a href="https://github.com/security">Security</a></li>
      </ul>

      <p>&copy; 2012 <span title="0.09186s from fe17.rs.github.com">GitHub</span> Inc. All rights reserved.</p>
    </div><!-- /#legal or /#legal_ie-->

  </div><!-- /.site -->
</div><!-- /.lower_footer -->

      </div><!-- /#footer -->

    

<div id="keyboard_shortcuts_pane" class="instapaper_ignore readability-extra" style="display:none">
  <h2>Keyboard Shortcuts <small><a href="#" class="js-see-all-keyboard-shortcuts">(see all)</a></small></h2>

  <div class="columns threecols">
    <div class="column first">
      <h3>Site wide shortcuts</h3>
      <dl class="keyboard-mappings">
        <dt>s</dt>
        <dd>Focus command bar</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>?</dt>
        <dd>Bring up this help dialog</dd>
      </dl>
    </div><!-- /.column.first -->

    <div class="column middle" style='display:none'>
      <h3>Commit list</h3>
      <dl class="keyboard-mappings">
        <dt>j</dt>
        <dd>Move selection down</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>k</dt>
        <dd>Move selection up</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>c <em>or</em> o <em>or</em> enter</dt>
        <dd>Open commit</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>y</dt>
        <dd>Expand URL to its canonical form</dd>
      </dl>
    </div><!-- /.column.first -->

    <div class="column last js-hidden-pane" style='display:none'>
      <h3>Pull request list</h3>
      <dl class="keyboard-mappings">
        <dt>j</dt>
        <dd>Move selection down</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>k</dt>
        <dd>Move selection up</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt>o <em>or</em> enter</dt>
        <dd>Open issue</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt><span class="platform-mac">⌘</span><span class="platform-other">ctrl</span> <em>+</em> enter</dt>
        <dd>Submit comment</dd>
      </dl>
      <dl class="keyboard-mappings">
        <dt><span class="platform-mac">⌘</span><span class="platform-other">ctrl</span> <em>+</em> shift p</dt>
        <dd>Preview comment</dd>
      </dl>
    </div><!-- /.columns.last -->

  </div><!-- /.columns.equacols -->

  <div class="js-hidden-pane" style='display:none'>
    <div class="rule"></div>

    <h3>Issues</h3>

    <div class="columns threecols">
      <div class="column first">
        <dl class="keyboard-mappings">
          <dt>j</dt>
          <dd>Move selection down</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>k</dt>
          <dd>Move selection up</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>x</dt>
          <dd>Toggle selection</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>o <em>or</em> enter</dt>
          <dd>Open issue</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt><span class="platform-mac">⌘</span><span class="platform-other">ctrl</span> <em>+</em> enter</dt>
          <dd>Submit comment</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt><span class="platform-mac">⌘</span><span class="platform-other">ctrl</span> <em>+</em> shift p</dt>
          <dd>Preview comment</dd>
        </dl>
      </div><!-- /.column.first -->
      <div class="column last">
        <dl class="keyboard-mappings">
          <dt>c</dt>
          <dd>Create issue</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>l</dt>
          <dd>Create label</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>i</dt>
          <dd>Back to inbox</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>u</dt>
          <dd>Back to issues</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>/</dt>
          <dd>Focus issues search</dd>
        </dl>
      </div>
    </div>
  </div>

  <div class="js-hidden-pane" style='display:none'>
    <div class="rule"></div>

    <h3>Issues Dashboard</h3>

    <div class="columns threecols">
      <div class="column first">
        <dl class="keyboard-mappings">
          <dt>j</dt>
          <dd>Move selection down</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>k</dt>
          <dd>Move selection up</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>o <em>or</em> enter</dt>
          <dd>Open issue</dd>
        </dl>
      </div><!-- /.column.first -->
    </div>
  </div>

  <div class="js-hidden-pane" style='display:none'>
    <div class="rule"></div>

    <h3>Network Graph</h3>
    <div class="columns equacols">
      <div class="column first">
        <dl class="keyboard-mappings">
          <dt><span class="badmono">←</span> <em>or</em> h</dt>
          <dd>Scroll left</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt><span class="badmono">→</span> <em>or</em> l</dt>
          <dd>Scroll right</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt><span class="badmono">↑</span> <em>or</em> k</dt>
          <dd>Scroll up</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt><span class="badmono">↓</span> <em>or</em> j</dt>
          <dd>Scroll down</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>t</dt>
          <dd>Toggle visibility of head labels</dd>
        </dl>
      </div><!-- /.column.first -->
      <div class="column last">
        <dl class="keyboard-mappings">
          <dt>shift <span class="badmono">←</span> <em>or</em> shift h</dt>
          <dd>Scroll all the way left</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>shift <span class="badmono">→</span> <em>or</em> shift l</dt>
          <dd>Scroll all the way right</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>shift <span class="badmono">↑</span> <em>or</em> shift k</dt>
          <dd>Scroll all the way up</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>shift <span class="badmono">↓</span> <em>or</em> shift j</dt>
          <dd>Scroll all the way down</dd>
        </dl>
      </div><!-- /.column.last -->
    </div>
  </div>

  <div class="js-hidden-pane" >
    <div class="rule"></div>
    <div class="columns threecols">
      <div class="column first js-hidden-pane" >
        <h3>Source Code Browsing</h3>
        <dl class="keyboard-mappings">
          <dt>t</dt>
          <dd>Activates the file finder</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>l</dt>
          <dd>Jump to line</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>w</dt>
          <dd>Switch branch/tag</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>y</dt>
          <dd>Expand URL to its canonical form</dd>
        </dl>
      </div>
    </div>
  </div>

  <div class="js-hidden-pane" style='display:none'>
    <div class="rule"></div>
    <div class="columns threecols">
      <div class="column first">
        <h3>Browsing Commits</h3>
        <dl class="keyboard-mappings">
          <dt><span class="platform-mac">⌘</span><span class="platform-other">ctrl</span> <em>+</em> enter</dt>
          <dd>Submit comment</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>escape</dt>
          <dd>Close form</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>p</dt>
          <dd>Parent commit</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>o</dt>
          <dd>Other parent commit</dd>
        </dl>
      </div>
    </div>
  </div>

  <div class="js-hidden-pane" style='display:none'>
    <div class="rule"></div>
    <h3>Notifications</h3>

    <div class="columns threecols">
      <div class="column first">
        <dl class="keyboard-mappings">
          <dt>j</dt>
          <dd>Move selection down</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>k</dt>
          <dd>Move selection up</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>o <em>or</em> enter</dt>
          <dd>Open notification</dd>
        </dl>
      </div><!-- /.column.first -->

      <div class="column second">
        <dl class="keyboard-mappings">
          <dt>e <em>or</em> shift i <em>or</em> y</dt>
          <dd>Mark as read</dd>
        </dl>
        <dl class="keyboard-mappings">
          <dt>shift m</dt>
          <dd>Mute thread</dd>
        </dl>
      </div><!-- /.column.first -->
    </div>
  </div>

</div>

    <div id="markdown-help" class="instapaper_ignore readability-extra">
  <h2>Markdown Cheat Sheet</h2>

  <div class="cheatsheet-content">

  <div class="mod">
    <div class="col">
      <h3>Format Text</h3>
      <p>Headers</p>
      <pre>
# This is an &lt;h1&gt; tag
## This is an &lt;h2&gt; tag
###### This is an &lt;h6&gt; tag</pre>
     <p>Text styles</p>
     <pre>
*This text will be italic*
_This will also be italic_
**This text will be bold**
__This will also be bold__

*You **can** combine them*
</pre>
    </div>
    <div class="col">
      <h3>Lists</h3>
      <p>Unordered</p>
      <pre>
* Item 1
* Item 2
  * Item 2a
  * Item 2b</pre>
     <p>Ordered</p>
     <pre>
1. Item 1
2. Item 2
3. Item 3
   * Item 3a
   * Item 3b</pre>
    </div>
    <div class="col">
      <h3>Miscellaneous</h3>
      <p>Images</p>
      <pre>
![GitHub Logo](/images/logo.png)
Format: ![Alt Text](url)
</pre>
     <p>Links</p>
     <pre>
http://github.com - automatic!
[GitHub](http://github.com)</pre>
<p>Blockquotes</p>
     <pre>
As Kanye West said:

> We're living the future so
> the present is our past.
</pre>
    </div>
  </div>
  <div class="rule"></div>

  <h3>Code Examples in Markdown</h3>
  <div class="col">
      <p>Syntax highlighting with <a href="http://github.github.com/github-flavored-markdown/" title="GitHub Flavored Markdown" target="_blank">GFM</a></p>
      <pre>
```javascript
function fancyAlert(arg) {
  if(arg) {
    $.facebox({div:'#foo'})
  }
}
```</pre>
    </div>
    <div class="col">
      <p>Or, indent your code 4 spaces</p>
      <pre>
Here is a Python code example
without syntax highlighting:

    def foo:
      if not bar:
        return true</pre>
    </div>
    <div class="col">
      <p>Inline code for comments</p>
      <pre>
I think you should use an
`&lt;addr&gt;` element here instead.</pre>
    </div>
  </div>

  </div>
</div>


    <div id="ajax-error-message" class="flash flash-error">
      <span class="mini-icon mini-icon-exclamation"></span>
      Something went wrong with that request. Please try again.
      <a href="#" class="mini-icon mini-icon-remove-close ajax-error-dismiss"></a>
    </div>

    <div id="logo-popup">
      <h2>Looking for the GitHub logo?</h2>
      <ul>
        <li>
          <h4>GitHub Logo</h4>
          <a href="http://github-media-downloads.s3.amazonaws.com/GitHub_Logos.zip"><img alt="Github_logo" src="https://a248.e.akamai.net/assets.github.com/images/modules/about_page/github_logo.png?1340659530" /></a>
          <a href="http://github-media-downloads.s3.amazonaws.com/GitHub_Logos.zip" class="minibutton download">Download</a>
        </li>
        <li>
          <h4>The Octocat</h4>
          <a href="http://github-media-downloads.s3.amazonaws.com/Octocats.zip"><img alt="Octocat" src="https://a248.e.akamai.net/assets.github.com/images/modules/about_page/octocat.png?1340659530" /></a>
          <a href="http://github-media-downloads.s3.amazonaws.com/Octocats.zip" class="minibutton download">Download</a>
        </li>
      </ul>
    </div>

    
    
    <span id='server_response_time' data-time='0.09445' data-host='fe17'></span>
    
  </body>
</html>

