"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  ArrowRight,
  Play,
  Sparkles,
  Upload,
  Palette,
  Wand2,
  Download,
  Check,
  Star,
  Instagram,
  Building2,
  TrendingUp,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
              Keylia
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <Link
              href="#features"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Features
            </Link>
            <Link
              href="#how-it-works"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              How It Works
            </Link>
            <Link
              href="#pricing"
              className="text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
            >
              Pricing
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
            <Button
              asChild
              className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 shadow-lg shadow-blue-500/25"
            >
              <Link href="/signup">
                Start Free Trial
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-20 pb-32">
          {/* Background decorations */}
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-100 rounded-full blur-3xl opacity-60" />
            <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-100 rounded-full blur-3xl opacity-60" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-blue-50 to-cyan-50 rounded-full blur-3xl opacity-40" />
          </div>

          <div className="container">
            <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 border border-blue-100 px-4 py-2 mb-8">
                <Sparkles className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-700">
                  AI-Powered Content for Real Estate Agents
                </span>
              </div>

              {/* Main heading */}
              <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-gray-900 leading-[1.1]">
                Turn Listings Into{" "}
                <span className="bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 bg-clip-text text-transparent">
                  Scroll-Stopping
                </span>{" "}
                Content
              </h1>

              {/* Subheading */}
              <p className="mt-6 text-xl text-gray-600 max-w-2xl leading-relaxed">
                Create stunning social media posts, captions, and hashtags for
                your property listings in seconds. Just upload photos and let AI
                do the magic.
              </p>

              {/* CTA buttons */}
              <div className="mt-10 flex flex-col sm:flex-row gap-4">
                <Button
                  size="lg"
                  asChild
                  className="h-14 px-8 text-lg bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 shadow-xl shadow-blue-500/25"
                >
                  <Link href="/signup">
                    Start Free Trial
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Link>
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  asChild
                  className="h-14 px-8 text-lg border-2"
                >
                  <Link href="#demo">
                    <Play className="mr-2 h-5 w-5" />
                    Watch Demo
                  </Link>
                </Button>
              </div>

              {/* Social proof */}
              <div className="mt-10 flex items-center gap-8 text-sm text-gray-500">
                <div className="flex items-center gap-2">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>No credit card required</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>5 free generations</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="h-5 w-5 text-green-500" />
                  <span>Cancel anytime</span>
                </div>
              </div>
            </div>

            {/* Hero Image/Demo */}
            <div className="mt-20 relative max-w-5xl mx-auto" id="demo">
              <div className="relative rounded-2xl border border-gray-200 bg-white shadow-2xl shadow-gray-200/50 overflow-hidden">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-200">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                  </div>
                  <div className="flex-1 flex justify-center">
                    <div className="px-4 py-1 rounded-md bg-gray-100 text-xs text-gray-500">
                      app.keylia.io
                    </div>
                  </div>
                </div>
                {/* Dashboard preview */}
                <div className="aspect-[16/9] bg-gradient-to-br from-gray-50 to-gray-100 p-8">
                  <div className="h-full rounded-xl bg-white border border-gray-200 shadow-sm flex items-center justify-center">
                    <div className="text-center p-8">
                      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
                        <Play className="h-10 w-10 text-white" />
                      </div>
                      <p className="text-lg font-medium text-gray-900">
                        See Keylia in Action
                      </p>
                      <p className="mt-2 text-gray-500">
                        Watch how agents create content 10x faster
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating cards */}
              <div className="absolute -left-8 top-1/4 hidden lg:block">
                <Card className="w-64 shadow-xl shadow-gray-200/50 border-gray-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center">
                        <Instagram className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">Instagram Ready</p>
                        <p className="text-xs text-gray-500">
                          Optimized formats
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="absolute -right-8 top-1/3 hidden lg:block">
                <Card className="w-64 shadow-xl shadow-gray-200/50 border-gray-200">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                        <Wand2 className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">AI-Powered</p>
                        <p className="text-xs text-gray-500">
                          Smart captions & hashtags
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-16 bg-gray-50 border-y border-gray-100">
          <div className="container">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {[
                { value: "10x", label: "Faster Content Creation" },
                { value: "500+", label: "Happy Agents" },
                { value: "50K+", label: "Posts Generated" },
                { value: "4.9", label: "Average Rating", icon: Star },
              ].map((stat, i) => (
                <div key={i} className="text-center">
                  <div className="flex items-center justify-center gap-1">
                    <span className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                      {stat.value}
                    </span>
                    {stat.icon && (
                      <Star className="h-6 w-6 text-yellow-400 fill-yellow-400" />
                    )}
                  </div>
                  <p className="mt-2 text-gray-600">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-24">
          <div className="container">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-4xl font-bold text-gray-900">
                Everything You Need to{" "}
                <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                  Stand Out
                </span>
              </h2>
              <p className="mt-4 text-xl text-gray-600">
                Professional content that makes your listings shine on social
                media
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  icon: Wand2,
                  title: "AI Captions",
                  description:
                    "Compelling property descriptions that highlight key features and drive engagement",
                  color: "from-blue-500 to-cyan-500",
                  bgColor: "bg-blue-50",
                },
                {
                  icon: TrendingUp,
                  title: "Smart Hashtags",
                  description:
                    "Trending and location-based hashtags to maximize your reach and visibility",
                  color: "from-purple-500 to-pink-500",
                  bgColor: "bg-purple-50",
                },
                {
                  icon: Palette,
                  title: "Brand Kit",
                  description:
                    "Save your colors, logo, and style preferences for consistent branding",
                  color: "from-orange-500 to-red-500",
                  bgColor: "bg-orange-50",
                },
                {
                  icon: Building2,
                  title: "Listing Manager",
                  description:
                    "Organize all your properties in one place with photos and details",
                  color: "from-green-500 to-emerald-500",
                  bgColor: "bg-green-50",
                },
                {
                  icon: Download,
                  title: "Easy Export",
                  description:
                    "Download images and copy captions with one click, ready to post",
                  color: "from-cyan-500 to-blue-500",
                  bgColor: "bg-cyan-50",
                },
                {
                  icon: Instagram,
                  title: "Multi-Platform",
                  description:
                    "Optimized formats for Instagram, Facebook, TikTok, and more",
                  color: "from-pink-500 to-rose-500",
                  bgColor: "bg-pink-50",
                },
              ].map((feature, i) => (
                <Card
                  key={i}
                  className="group border-gray-200 hover:border-gray-300 hover:shadow-lg transition-all duration-300"
                >
                  <CardContent className="p-6">
                    <div
                      className={`inline-flex h-12 w-12 items-center justify-center rounded-xl ${feature.bgColor} mb-4`}
                    >
                      <feature.icon
                        className={`h-6 w-6 bg-gradient-to-r ${feature.color} bg-clip-text`}
                        style={{
                          stroke: `url(#gradient-${i})`,
                        }}
                      />
                      <svg width="0" height="0">
                        <defs>
                          <linearGradient id={`gradient-${i}`}>
                            <stop offset="0%" stopColor="#3b82f6" />
                            <stop offset="100%" stopColor="#06b6d4" />
                          </linearGradient>
                        </defs>
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600">{feature.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="py-24 bg-gray-50">
          <div className="container">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-4xl font-bold text-gray-900">
                Content in{" "}
                <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                  3 Simple Steps
                </span>
              </h2>
              <p className="mt-4 text-xl text-gray-600">
                From listing photos to social-ready content in minutes
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {[
                {
                  step: "01",
                  icon: Upload,
                  title: "Upload Photos",
                  description:
                    "Add your listing with property details and photos",
                },
                {
                  step: "02",
                  icon: Wand2,
                  title: "Generate Content",
                  description:
                    "AI creates captions, hashtags, and social posts",
                },
                {
                  step: "03",
                  icon: Download,
                  title: "Download & Post",
                  description: "Export and share to all your social platforms",
                },
              ].map((item, i) => (
                <div key={i} className="relative text-center">
                  {i < 2 && (
                    <div className="hidden md:block absolute top-12 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-blue-200 to-cyan-200" />
                  )}
                  <div className="relative">
                    <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-2xl bg-white border-2 border-gray-200 shadow-lg">
                      <item.icon className="h-10 w-10 text-blue-600" />
                    </div>
                    <span className="absolute -top-2 -right-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-sm font-bold shadow-lg">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-24">
          <div className="container">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-4xl font-bold text-gray-900">
                Simple,{" "}
                <span className="bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                  Transparent
                </span>{" "}
                Pricing
              </h2>
              <p className="mt-4 text-xl text-gray-600">
                Start free, upgrade when you&apos;re ready
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
              {/* Starter Plan */}
              <Card className="border-gray-200 hover:border-gray-300 transition-colors">
                <CardContent className="p-8">
                  <h3 className="text-2xl font-bold text-gray-900">Starter</h3>
                  <p className="mt-2 text-gray-600">
                    Perfect for individual agents
                  </p>
                  <div className="mt-6 flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-gray-900">
                      $49
                    </span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <ul className="mt-8 space-y-4">
                    {[
                      "20 content pieces per month",
                      "All template styles",
                      "AI captions & hashtags",
                      "HD image exports",
                      "Email support",
                    ].map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
                        <span className="text-gray-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full mt-8 h-12"
                    variant="outline"
                    asChild
                  >
                    <Link href="/signup">Start Free Trial</Link>
                  </Button>
                </CardContent>
              </Card>

              {/* Pro Plan */}
              <Card className="border-2 border-blue-500 relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
                  POPULAR
                </div>
                <CardContent className="p-8">
                  <h3 className="text-2xl font-bold text-gray-900">Pro</h3>
                  <p className="mt-2 text-gray-600">For busy agents & teams</p>
                  <div className="mt-6 flex items-baseline gap-1">
                    <span className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                      $99
                    </span>
                    <span className="text-gray-600">/month</span>
                  </div>
                  <ul className="mt-8 space-y-4">
                    {[
                      "Unlimited content pieces",
                      "All template styles",
                      "AI captions & hashtags",
                      "HD image exports",
                      "Priority support",
                      "Custom branding",
                      "Batch generation",
                    ].map((feature, i) => (
                      <li key={i} className="flex items-center gap-3">
                        <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
                        <span className="text-gray-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full mt-8 h-12 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600"
                    asChild
                  >
                    <Link href="/signup">Start Free Trial</Link>
                  </Button>
                </CardContent>
              </Card>
            </div>

            <p className="text-center mt-8 text-gray-500">
              All plans include a 7-day free trial. No credit card required.
            </p>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 bg-gradient-to-br from-blue-600 via-blue-700 to-cyan-600 relative overflow-hidden">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-10">
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
              }}
            />
          </div>

          <div className="container relative">
            <div className="text-center max-w-3xl mx-auto">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Ready to Transform Your Listings?
              </h2>
              <p className="text-xl text-blue-100 mb-10">
                Join hundreds of agents creating scroll-stopping content with
                Keylia. Start your free trial today.
              </p>
              <Button
                size="lg"
                asChild
                className="h-14 px-10 text-lg bg-white text-blue-600 hover:bg-blue-50 shadow-xl"
              >
                <Link href="/signup">
                  Get Started Free
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-12 bg-white">
        <div className="container">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold text-gray-900">Keylia</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-gray-600">
              <Link href="/terms" className="hover:text-gray-900">
                Terms
              </Link>
              <Link href="/privacy" className="hover:text-gray-900">
                Privacy
              </Link>
              <Link href="mailto:support@keylia.io" className="hover:text-gray-900">
                Contact
              </Link>
            </div>
            <p className="text-sm text-gray-500">
              © {new Date().getFullYear()} Keylia. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
