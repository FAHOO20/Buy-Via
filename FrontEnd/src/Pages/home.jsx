import "../style.css"
import Img_Slider from "../Components/Img_Slider/Img_Slider"
import SimpleImageSlider from "react-simple-image-slider";
import SearchResults from "./SearchResults";
import HorizontalScrollView from "../Components/HorizontalScrollView/HorizontalScrollView";
import PopularCategories from "../Components/PopularCategories/PopularCategories";


const home = () => {
  return (
    <main>
    <Img_Slider/>
    <PopularCategories></PopularCategories>
    <HorizontalScrollView prompt="Apple Iphone" />
    <HorizontalScrollView prompt="Samsung Galaxy" />
    <HorizontalScrollView prompt="huawei laptop" />

    </main>
  );
}

export default home