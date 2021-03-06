#!/usr/bin/env python

import os
import youtube_dl
import re
import datetime
import argparse

import opentimelineio as otio


def process_youtube_description(description_file):
    """Function should parse the Youtube description to find any table-of-
    contents entries.The table-of-contents entries will contain a timestamp
    paired with a chapter title. For example: (00:12:15) Thor fights Thanos

    The function should return an array of all such timestamps
    and chapter titles.

    :param description_file: contains the Youtube description.
    :rtype: list
    """
    with open(description_file) as f:
        lines = f.readlines()

    # Should match the following timestamp patterns:
    # 01:34:21 chapter title
    # 1:34:21 chapter title
    # 34:21 chapter title
    # 4:21 chapter title
    # (4:21) chapter title
    # [4:21] chapter title

    pattern = re.compile(r"((?:\d+:)+\d{2})[\),\]]*\s(.+)")
    chapters = []

    for line in lines:
        matches = pattern.findall(line)
        if matches:
            chapters.append(matches[0])

    return chapters


def convert_time_stamp_to_seconds(time_stamp):
    time_split = time_stamp.split(":")
    time_split.reverse()
    hours = 0
    minutes = 0
    seconds = 0

    if len(time_split) > 0:
        seconds = time_split[0]
    if len(time_split) > 1:
        minutes = time_split[1]
    if len(time_split) > 2:
        hours = time_split[2]

    timeDelta = datetime.timedelta(
        hours=int(hours), minutes=int(minutes), seconds=int(seconds)
    )

    return timeDelta.total_seconds()


def create_markers(chapters, fps):
    markers = []

    for chapter in chapters:
        seconds = convert_time_stamp_to_seconds(chapter[0])

        marker = otio.schema.Marker()

        otio.opentime.from_seconds(seconds, fps)

        marker.marked_range = otio.opentime.TimeRange(
            start_time=otio.opentime.from_seconds(seconds, fps),
            duration=otio.opentime.from_seconds(
                0, fps
            ),  # We are setting the duration of each marker to be 0 frames.
        )

        marker.color = otio.schema.MarkerColor.RED

        marker.name = chapter[1]
        markers.append(marker)

    return markers


def download_from_youtube(youtubeURL, skip_video_download):
    ydl_opts = {
        "outtmpl": os.path.join("tmp", "%(id)s.mp4"),
        "noplaylist": True,
        "quiet": True,
        "writedescription": True,
        "skip_download": skip_video_download,
    }

    # Download the youtube video and description onto local computer
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        dictMeta = ydl.extract_info(
            "https://www.youtube.com/watch?v={sID}".format(sID=youtubeURL),
            download=True,
        )

    return dictMeta


def create_timeline(dictMeta, video_file, description_file, otio_file):
    # Steps for importing the video into OTIO
    # 1. Create a TimeLine object
    timeline = otio.schema.Timeline()
    timeline.name = "Youtube Demo"

    # 2. Create a Track on the timeline
    track = otio.schema.Track()
    track.name = "Videos"
    timeline.tracks.append(track)

    # 3. Find out how long the youtube video is
    totalFrames = dictMeta["duration"] * dictMeta["fps"]

    available_range = otio.opentime.TimeRange(
        otio.opentime.from_seconds(0, dictMeta["fps"]),
        otio.opentime.from_seconds(dictMeta["duration"], dictMeta["fps"]),
    )

    # 4. Create a media_reference (contians the file path of the youtube video)

    media_reference = otio.schema.ExternalReference(
        target_url=video_file,
        available_range=available_range,
        metadata={"YouTube": {"original_url": dictMeta["webpage_url"]}},
    )

    # 5. Create a Clip and set the media_reference (based on what we
    # found in step 4)
    clip = otio.schema.Clip(
        name=dictMeta["title"],
        metadata={
            "YouTube": {
                "upload_date": dictMeta["upload_date"],
                "view_count": dictMeta["view_count"],
                "categories": dictMeta["categories"],
            }
        },
    )
    clip.media_reference = media_reference

    # 6. Append the Clip to the Track
    track.append(clip)

    # 7. Process the youtube description and insert Markers into the timeline
    chapters = process_youtube_description(description_file)

    markers = create_markers(chapters, dictMeta["fps"])

    clip.markers.extend(markers)

    # save the timeline as .otio file
    otio.adapters.write_to_file(timeline, otio_file)
    print("SAVED: {0} with {1} markers.".format(otio_file, len(markers)))


def run_demo(youtubeVideoID, skip_video_download):
    dictMeta = download_from_youtube(youtubeVideoID, skip_video_download)

    video_file = os.path.join("tmp", youtubeVideoID + ".mp4")
    description_file = os.path.join("tmp", youtubeVideoID + ".description")
    otio_file = youtubeVideoID + ".otio"

    create_timeline(dictMeta, video_file, description_file, otio_file)

    return {
        "video_file": video_file,
        "description_file": description_file,
        "otio_file": otio_file,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "youtubeVideoID",
        help="""The ID of the youtube video you would like to download.For
        example, in the following URL
        (https://www.youtube.com/watch?v=es6LBWB_I4E)
        ,the ID is es6LBWB_I4E.""",
    )
    parser.add_argument(
        "--skip-video-download",
        help="Do not download the youtube video",
        action="store_true",
    )

    args = parser.parse_args()
    youtubeVideoID = args.youtubeVideoID
    skip_video_download = args.skip_video_download

    run_demo(youtubeVideoID, skip_video_download)


if __name__ == "__main__":
    main()
