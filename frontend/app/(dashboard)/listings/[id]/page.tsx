"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { trpc } from "@/lib/trpc/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import {
  ArrowLeft,
  Bed,
  Bath,
  Square,
  MapPin,
  Sparkles,
  Loader2,
  Download,
  Video,
} from "lucide-react";
import Link from "next/link";

// Type definitions for proper TypeScript inference
interface Listing {
  id: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  price: number;
  bedrooms: number;
  bathrooms: number;
  sqft: number;
  property_type: string;
  status: string;
  description: string | null;
  features: string[] | null;
  photos: string[] | null;
}

interface ContentPiece {
  id: string;
  content_type: string;
  caption: string | null;
  hashtags: string[] | null;
}

const CONTENT_TYPES = [
  { value: "just_listed", label: "Just Listed", description: "Announce your new listing" },
  { value: "open_house", label: "Open House", description: "Promote your open house event" },
  { value: "price_drop", label: "Price Drop", description: "Highlight a price reduction" },
  { value: "coming_soon", label: "Coming Soon", description: "Tease an upcoming listing" },
  { value: "just_sold", label: "Just Sold", description: "Celebrate a successful sale" },
] as const;

const PLATFORMS = [
  { value: "instagram", label: "Instagram", icon: "📸", description: "Long captions, 15-20 hashtags" },
  { value: "facebook", label: "Facebook", icon: "👥", description: "Conversational, 3-5 hashtags" },
  { value: "twitter", label: "X / Twitter", icon: "𝕏", description: "280 chars max, 1-2 hashtags" },
] as const;

export default function ListingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const listingId = params.id as string;

  const [selectedType, setSelectedType] = useState<string>("just_listed");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("instagram");
  const [generatedContent, setGeneratedContent] = useState<{
    headline: string;
    caption: string;
    hashtags: string[];
    platform: string;
  } | null>(null);

  const { data: listingData, isLoading } = trpc.listing.get.useQuery({ id: listingId });
  const { data: existingContentData } = trpc.content.list.useQuery({ listing_id: listingId });

  // Cast for proper TypeScript inference
  const listing = listingData as Listing | null | undefined;
  const existingContent = existingContentData as { content: ContentPiece[]; total: number } | undefined;

  const generateContent = trpc.ai.generateContent.useMutation();
  const createContentPiece = trpc.content.create.useMutation();
  const trackDownload = trpc.content.trackDownload.useMutation();

  const handleGenerate = async () => {
    try {
      const result = await generateContent.mutateAsync({
        listing_id: listingId,
        content_type: selectedType as "just_listed" | "just_sold" | "open_house" | "price_drop" | "coming_soon",
        platform: selectedPlatform as "instagram" | "facebook" | "twitter",
      });

      setGeneratedContent({
        headline: result.headline,
        caption: result.caption,
        hashtags: result.hashtags,
        platform: result.platform,
      });

      // Save to database
      await createContentPiece.mutateAsync({
        listing_id: listingId,
        content_type: selectedType as "just_listed" | "just_sold" | "open_house" | "price_drop" | "coming_soon",
        caption: result.caption,
        hashtags: result.hashtags,
      });

      toast({
        title: "Content generated!",
        description: "Your caption and hashtags are ready.",
      });
    } catch {
      toast({
        title: "Generation failed",
        description: "Could not generate content. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDownload = async (contentId: string) => {
    await trackDownload.mutateAsync({ id: contentId });
    toast({
      title: "Downloaded!",
      description: "Content downloaded successfully.",
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied!",
      description: "Caption copied to clipboard.",
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!listing) {
    return (
      <div className="container py-8">
        <p className="text-muted-foreground">Listing not found</p>
        <Button variant="link" onClick={() => router.back()}>
          Go back
        </Button>
      </div>
    );
  }

  return (
    <div className="container py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">{listing.address}</h1>
          <p className="text-muted-foreground flex items-center gap-1">
            <MapPin className="w-4 h-4" />
            {listing.city}, {listing.state} {listing.zip}
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Listing Details */}
        <div className="lg:col-span-1 space-y-6">
          {/* Photos */}
          {listing.photos && listing.photos.length > 0 && (
            <Card>
              <CardContent className="p-0">
                <img
                  src={listing.photos[0]}
                  alt={listing.address}
                  className="w-full aspect-video object-cover rounded-t-xl"
                />
                {listing.photos.length > 1 && (
                  <div className="p-4 grid grid-cols-4 gap-2">
                    {listing.photos.slice(1, 5).map((photo, i) => (
                      <img
                        key={i}
                        src={photo}
                        alt={`Photo ${i + 2}`}
                        className="aspect-square object-cover rounded"
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Property Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-3xl font-bold">
                ${listing.price.toLocaleString()}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-6 text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Bed className="w-4 h-4" /> {listing.bedrooms} bed
                </span>
                <span className="flex items-center gap-1">
                  <Bath className="w-4 h-4" /> {listing.bathrooms} bath
                </span>
                <span className="flex items-center gap-1">
                  <Square className="w-4 h-4" /> {listing.sqft.toLocaleString()} sqft
                </span>
              </div>

              <div className="space-y-2">
                <span className="text-sm font-medium">Type</span>
                <p className="text-muted-foreground capitalize">
                  {listing.property_type.replace("_", " ")}
                </p>
              </div>

              {listing.features && listing.features.length > 0 && (
                <div className="space-y-2">
                  <span className="text-sm font-medium">Features</span>
                  <div className="flex flex-wrap gap-2">
                    {listing.features.map((feature) => (
                      <span
                        key={feature}
                        className="px-2 py-1 bg-muted rounded-full text-xs"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {listing.description && (
                <div className="space-y-2">
                  <span className="text-sm font-medium">Description</span>
                  <p className="text-sm text-muted-foreground">
                    {listing.description}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tour Video Card */}
          <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="w-5 h-5 text-blue-600" />
                Tour Video
              </CardTitle>
              <CardDescription>
                Create an AI-powered video tour of this property
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link href={`/listings/${listingId}/generate-video`}>
                <Button className="w-full bg-blue-600 hover:bg-blue-700">
                  <Video className="w-4 h-4 mr-2" />
                  Generate Tour Video
                </Button>
              </Link>
              <p className="text-xs text-muted-foreground text-center mt-3">
                AI-generated video with voiceover • 15s, 30s, or 60s
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Content Generation */}
        <div className="lg:col-span-2 space-y-6">
          {/* Generate New Content */}
          <Card>
            <CardHeader>
              <CardTitle>Generate Content</CardTitle>
              <CardDescription>
                Create AI-powered captions and hashtags for social media
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Content Type Selection */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {CONTENT_TYPES.map((type) => (
                  <button
                    key={type.value}
                    type="button"
                    onClick={() => setSelectedType(type.value)}
                    className={`
                      p-3 rounded-lg border text-left transition-all
                      ${selectedType === type.value
                        ? "border-primary bg-primary/5"
                        : "border-muted hover:border-primary/50"
                      }
                    `}
                  >
                    <span className="font-medium text-sm">{type.label}</span>
                    <p className="text-xs text-muted-foreground mt-1">
                      {type.description}
                    </p>
                  </button>
                ))}
              </div>

              {/* Platform Selection */}
              <div className="space-y-3 pt-4 border-t">
                <label className="text-sm font-medium">Platform</label>
                <div className="grid grid-cols-3 gap-3">
                  {PLATFORMS.map((platform) => (
                    <button
                      key={platform.value}
                      type="button"
                      onClick={() => setSelectedPlatform(platform.value)}
                      className={`
                        p-3 rounded-lg border text-center transition-all
                        ${selectedPlatform === platform.value
                          ? "border-primary bg-primary/5"
                          : "border-muted hover:border-primary/50"
                        }
                      `}
                    >
                      <span className="text-xl block mb-1">{platform.icon}</span>
                      <span className="font-medium text-sm">{platform.label}</span>
                      <p className="text-xs text-muted-foreground mt-1">
                        {platform.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleGenerate}
                disabled={generateContent.isPending}
                className="w-full"
              >
                {generateContent.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating for {PLATFORMS.find((p) => p.value === selectedPlatform)?.label}...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate for {PLATFORMS.find((p) => p.value === selectedPlatform)?.label}
                  </>
                )}
              </Button>

              {/* Generated Content Preview */}
              {generatedContent && (
                <div className="space-y-4 pt-4 border-t">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">Generated for</span>
                    <span className="px-2 py-1 bg-primary/10 text-primary text-xs rounded-full font-medium">
                      {PLATFORMS.find((p) => p.value === generatedContent.platform)?.label}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Headline</span>
                    </div>
                    <p className="text-lg font-semibold">{generatedContent.headline}</p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Caption</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(generatedContent.caption)}
                      >
                        Copy
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {generatedContent.caption}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Hashtags</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          copyToClipboard(generatedContent.hashtags.map((h) => `#${h}`).join(" "))
                        }
                      >
                        Copy
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {generatedContent.hashtags.map((tag) => (
                        <span
                          key={tag}
                          className="text-xs text-primary"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Previously Generated Content */}
          {existingContent && existingContent.content.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Previous Content</CardTitle>
                <CardDescription>
                  Content you&apos;ve generated for this listing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {existingContent.content.map((content) => (
                    <div
                      key={content.id}
                      className="p-4 border rounded-lg space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium capitalize">
                          {content.content_type.replace("_", " ")}
                        </span>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownload(content.id)}
                          >
                            <Download className="w-4 h-4 mr-1" />
                            Download
                          </Button>
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-3">
                        {content.caption}
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {content.hashtags?.slice(0, 5).map((tag) => (
                          <span key={tag} className="text-xs text-primary">
                            #{tag}
                          </span>
                        ))}
                        {content.hashtags && content.hashtags.length > 5 && (
                          <span className="text-xs text-muted-foreground">
                            +{content.hashtags.length - 5} more
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

        </div>
      </div>
    </div>
  );
}
